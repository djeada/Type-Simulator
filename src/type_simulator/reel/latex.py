"""
Live LaTeX preview for reels.

While a .tex file is typed, the reel shows its PDF next to the editor and
updates it after every line, like Overleaf or vimtex. Each line-end prefix is
made compilable (open environments, braces and math are closed), compiled in
parallel, and its last page rasterized. Lines that don't compile simply keep
the previous preview, exactly like a real live preview would.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageOps

logger = logging.getLogger(__name__)

LATEX_EXTENSIONS = {".tex", ".latex"}
_ENV_RE = re.compile(r"\\(begin|end)\{([^}]+)\}")
_COMMENT_RE = re.compile(r"(?<!\\)%.*")


def complete_prefix(source: str) -> Optional[str]:
    """
    Close whatever is still open at the end of a partial document so it can
    be compiled. Returns None before \\begin{document} (nothing to show yet).
    """
    if "\\begin{document}" not in source:
        return None
    body = "\n".join(_COMMENT_RE.sub("", line) for line in source.split("\n"))
    stack: List[str] = []
    for kind, env in _ENV_RE.findall(body):
        if kind == "begin":
            stack.append(env)
        elif stack and stack[-1] == env:
            stack.pop()
    plain = re.sub(r"\\[\\{}$%]", "", body)  # drop escaped characters
    tail = []
    if (plain.count("$") - 2 * plain.count("$$")) % 2:
        tail.append("$")
    if plain.count("\\[") > plain.count("\\]"):
        tail.append("\\]")
    tail.append("}" * max(0, plain.count("{") - plain.count("}")))
    tail.extend(f"\\end{{{env}}}" for env in reversed(stack))
    if "document" not in stack and "\\end{document}" not in body:
        tail.append("\\end{document}")
    tail = [t for t in tail if t]
    if not tail:
        return source
    # No blank line before the closers: that would be a paragraph break in math
    return source.rstrip("\n") + "\n" + "\n".join(tail) + "\n"


def compile_pdf(
    source: str,
    workdir: Path,
    engine: str = "pdflatex",
    texinputs: Optional[Path] = None,
) -> Optional[Path]:
    """Compile `source` in `workdir`; returns the PDF path, or None on errors."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "doc.tex").write_text(source, encoding="utf-8")
    env = dict(os.environ)
    if texinputs:
        env["TEXINPUTS"] = f"{texinputs}{os.pathsep}"
    try:
        result = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", "doc.tex"],
            cwd=workdir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return None
    pdf = workdir / "doc.pdf"
    return pdf if result.returncode == 0 and pdf.exists() else None


def _page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    match = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(match.group(1)) if match else 1


def _rasterize(pdf: Path, page: int, dpi: float, out: Path) -> Image.Image:
    subprocess.run(
        ["pdftoppm", "-png", "-singlefile", "-r", f"{dpi:.2f}",
         "-f", str(page), "-l", str(page), str(pdf), str(out)],
        check=True,
    )  # fmt: skip
    with Image.open(f"{out}.png") as img:
        return img.convert("RGB")


def _ink_box(img: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """Bounding box of everything that isn't (nearly) white."""
    gray = ImageOps.invert(img.convert("L")).point(lambda v: 255 if v > 24 else 0)
    return gray.getbbox()


@dataclass
class Snapshot:
    image: Path  # last page, cropped to the text width and scaled to the pane
    page: int
    pages: int
    focus: int  # y of the lowest ink on the page, followed by the preview


@dataclass
class LatexPreview:
    size: Tuple[int, int]
    snapshots: List[Snapshot] = field(default_factory=list)
    # (characters typed, snapshot index) once that prefix compiles
    checkpoints: List[Tuple[int, int]] = field(default_factory=list)

    def image(self, index: int) -> Image.Image:
        if index < 0 or not self.snapshots:
            return Image.new("RGB", self.size, (255, 255, 255))
        return _view(
            self.snapshots[index].image, self.snapshots[index].focus, self.size
        )

    def label(self, index: int) -> str:
        if index < 0 or not self.snapshots:
            return ""
        snap = self.snapshots[index]
        return f"page {snap.page}/{snap.pages}"


@lru_cache(maxsize=8)
def _view(path: Path, focus: int, size: Tuple[int, int]) -> Image.Image:
    """The part of the page shown in the pane: follows the newest content."""
    w, h = size
    with Image.open(path) as page:
        page = page.convert("RGB")
    top = max(0, min(focus - int(h * 0.72), page.height - h))
    view = Image.new("RGB", size, (255, 255, 255))
    view.paste(page.crop((0, top, w, min(page.height, top + h))), (0, 0))
    return view


def _set_focus(snapshots: List[Snapshot]) -> None:
    """
    Point each snapshot at what just changed: the lowest row that differs from
    the previous snapshot of the same page. That's the newly typed content,
    and unlike the lowest ink it isn't fooled by the page number in the footer.
    """
    previous = None
    for snap in snapshots:
        with Image.open(snap.image) as img:
            current = img.convert("L")
        focus = None
        if (
            previous is not None
            and previous[0] == snap.page
            and previous[1].size == current.size
        ):
            box = (
                ImageChops.difference(previous[1], current)
                .point(lambda v: 255 if v > 40 else 0)
                .getbbox()
            )
            if box:
                focus = box[3]
            else:
                focus = previous[2]
        if focus is None:
            # New page: its body text, ignoring the bottom margin with the page number
            body = current.crop((0, 0, current.width, int(current.height * 0.9)))
            box = ImageOps.invert(body).point(lambda v: 255 if v > 24 else 0).getbbox()
            focus = box[3] if box else 0
        snap.focus = focus
        previous = (snap.page, current, focus)


def tools_available(engine: str = "pdflatex") -> List[str]:
    """Names of required programs that are missing."""
    return [t for t in (engine, "pdftoppm", "pdfinfo") if shutil.which(t) is None]


def build_preview(
    script: str,
    size: Tuple[int, int],
    out_dir: Path,
    engine: str = "pdflatex",
    texinputs: Optional[Path] = None,
) -> LatexPreview:
    """Compile every line-end prefix of `script` and rasterize the results."""
    missing = tools_available(engine)
    if missing:
        raise RuntimeError(f"LaTeX preview needs: {', '.join(missing)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    preview = LatexPreview(size)
    ends = [i + 1 for i, ch in enumerate(script) if ch == "\n"] + [len(script)]
    sources: Dict[int, str] = {}
    for pos in ends:
        completed = complete_prefix(script[:pos])
        if completed is not None:
            sources[pos] = completed

    unique = list(dict.fromkeys(sources.values()))
    logger.info("Compiling %d LaTeX preview states", len(unique))
    with tempfile.TemporaryDirectory(prefix="reel-tex-") as tmp:
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            pdfs = list(
                pool.map(
                    lambda job: compile_pdf(
                        job[1], Path(tmp) / str(job[0]), engine, texinputs
                    ),
                    enumerate(unique),
                )
            )
        compiled = {src: pdf for src, pdf in zip(unique, pdfs) if pdf}
        if not compiled:
            logger.warning("No prefix of the document compiled; preview stays empty")
            return preview
        final_pdf = (
            compiled.get(sources.get(len(script)), None) or list(compiled.values())[-1]
        )

        # Crop to the text width of the final document so the text is as large as possible
        boxes = []
        for page in range(1, _page_count(final_pdf) + 1):
            img = _rasterize(final_pdf, page, 36, Path(tmp) / f"probe{page}")
            box = _ink_box(img)
            if box:
                boxes.append((box[0] / img.width, box[2] / img.width))
        left = max(0.0, min(b[0] for b in boxes) - 0.04) if boxes else 0.0
        right = min(1.0, max(b[1] for b in boxes) + 0.04) if boxes else 1.0

        def rasterize(job):
            index, pdf = job
            pages = _page_count(pdf)
            try:
                probe = _rasterize(pdf, pages, 72, Path(tmp) / f"size{index}")
            except subprocess.CalledProcessError:
                return None  # e.g. an empty document
            dpi = 72 * size[0] / ((right - left) * probe.width)
            img = _rasterize(pdf, pages, dpi, Path(tmp) / f"page{index}")
            img = img.crop(
                (round(left * img.width), 0, round(right * img.width), img.height)
            )
            img = img.resize((size[0], round(img.height * size[0] / img.width)))
            path = out_dir / f"{index:04d}.png"
            img.save(path)
            return Snapshot(path, pages, pages, 0)

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            shots = list(pool.map(rasterize, enumerate(compiled.values())))
        index_of = {}
        for src, shot in zip(compiled, shots):
            if shot is not None:
                index_of[src] = len(preview.snapshots)
                preview.snapshots.append(shot)
        _set_focus(preview.snapshots)

    last = -1
    for pos in ends:
        src = sources.get(pos)
        if src in index_of and index_of[src] != last:
            last = index_of[src]
            preview.checkpoints.append((pos, last))
    logger.info(
        "LaTeX preview: %d of %d states compiled", len(preview.snapshots), len(unique)
    )
    return preview
