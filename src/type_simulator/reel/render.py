"""Draws reel frames with Pillow."""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from type_simulator.reel.terminal import Line, Run
from type_simulator.reel.themes import RGB, Theme
from type_simulator.reel.timeline import EDITOR, Scene

logger = logging.getLogger(__name__)

_FALLBACK_FONTS = {
    "monospace": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Menlo.ttc",
        "C:/Windows/Fonts/consola.ttf",
    ],
    "monospace:bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "C:/Windows/Fonts/consolab.ttf",
    ],
    "sans:bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
}

_TRAFFIC_LIGHTS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]


def find_font(pattern: str) -> Optional[str]:
    """Locate a font file via fontconfig, falling back to common paths."""
    if shutil.which("fc-match"):
        try:
            path = subprocess.check_output(
                ["fc-match", "-f", "%{file}", pattern], text=True, timeout=5
            ).strip()
            if path:
                return path
        except (subprocess.SubprocessError, OSError):
            pass
    for path in _FALLBACK_FONTS.get(pattern, []):
        try:
            ImageFont.truetype(path, 10)
            return path
        except OSError:
            continue
    return None


def _load_font(path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    if path:
        return ImageFont.truetype(path, size)
    logger.warning("No TrueType font found; using Pillow's default font")
    return ImageFont.load_default(size)


def _mix(a: RGB, b: RGB, amount: float) -> RGB:
    return tuple(int(x + (y - x) * amount) for x, y in zip(a, b))  # type: ignore


@dataclass
class Layout:
    width: int
    height: int
    scale: float
    window: Tuple[int, int, int, int]
    titlebar_h: int
    content: Tuple[int, int, int, int]
    font_size: int
    char_w: float
    line_h: int
    cols: int
    rows: int


def compute_layout(
    width: int, height: int, font_size: Optional[int], mono_path: Optional[str]
) -> Layout:
    scale = width / 1080
    portrait = height >= width
    side = int(54 * scale)
    if portrait:
        top, bottom = int(height * 0.19), int(height * 0.86)
    else:
        top, bottom = int(height * 0.2), int(height * 0.9)
    window = (side, top, width - side, bottom)
    titlebar_h = int(64 * scale)
    pad = int(26 * scale)
    content = (
        window[0] + pad,
        window[1] + titlebar_h + pad // 2,
        window[2] - pad,
        window[3] - pad // 2,
    )
    size = font_size or max(12, int(30 * scale))
    font = _load_font(mono_path, size)
    char_w = font.getlength("M")
    line_h = int(size * 1.38)
    cols = max(20, int((content[2] - content[0]) // char_w))
    rows = max(5, (content[3] - content[1]) // line_h)
    return Layout(
        width,
        height,
        scale,
        window,
        titlebar_h,
        content,
        size,
        char_w,
        line_h,
        cols,
        rows,
    )


def _wrap_runs(line: Sequence[Run], cols: int) -> List[List[Run]]:
    rows: List[List[Run]] = [[]]
    used = 0
    for text, color, bold in line:
        while text:
            room = cols - used
            if room <= 0:
                rows.append([])
                used, room = 0, cols
            part, text = text[:room], text[room:]
            rows[-1].append((part, color, bold))
            used += len(part)
    return rows


class FrameRenderer:
    def __init__(
        self,
        theme: Theme,
        layout: Layout,
        script: str,
        colors: Sequence[Optional[RGB]],
        filename: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        footer: Optional[str] = None,
        mono_path: Optional[str] = None,
        mono_bold_path: Optional[str] = None,
        title_font_path: Optional[str] = None,
    ):
        self.theme = theme
        self.layout = layout
        self.script = script
        self.colors = colors
        self.filename = filename
        self.font = _load_font(mono_path, layout.font_size)
        self.font_bold = _load_font(mono_bold_path or mono_path, layout.font_size)
        self.title_font_path = title_font_path
        total_lines = script.count("\n") + 1
        self.gutter = len(str(total_lines)) + 1
        self.code_cols = layout.cols - self.gutter - 1
        self._bases = {
            "shell": self._base(f"{theme.prompt}: ~", title, subtitle, footer),
            EDITOR: self._base(f"{filename} - vim", title, subtitle, footer),
        }
        self._scanlines = self._scanline_mask() if theme.scanlines else None
        self._cursor_line_bg = _mix(theme.window_bg, theme.fg, 0.07)

    # ------------------------------------------------------------------ #
    def render(self, scene: Scene, cursor_on: bool) -> Image.Image:
        img = self._bases[scene.mode].copy()
        draw = ImageDraw.Draw(img)
        if scene.mode == EDITOR:
            self._draw_editor(draw, scene, cursor_on)
        else:
            self._draw_shell(draw, scene.shell, cursor_on)
        if self._scanlines is not None:
            box = self.layout.content
            region = img.crop(box)
            img.paste(ImageChops.multiply(region, self._scanlines), box[:2])
        return img

    def draw_progress(self, img: Image.Image, progress: float) -> None:
        lay = self.layout
        h = max(4, int(8 * lay.scale))
        w = int(lay.width * max(0.0, min(1.0, progress)))
        if w > 0:
            ImageDraw.Draw(img).rectangle(
                (0, lay.height - h, w, lay.height), fill=self.theme.accent
            )

    # ------------------------------------------------------------------ #
    def _cell(self, col: int, row: int) -> Tuple[int, int]:
        x0, y0 = self.layout.content[:2]
        return int(x0 + col * self.layout.char_w), y0 + row * self.layout.line_h

    def _draw_runs(self, draw, runs: Sequence[Run], col: int, row: int) -> int:
        for text, color, bold in runs:
            x, y = self._cell(col, row)
            draw.text(
                (x, y),
                text,
                font=self.font_bold if bold else self.font,
                fill=color or self.theme.fg,
            )
            col += len(text)
        return col

    def _draw_cursor(self, draw, col: int, row: int) -> None:
        x, y = self._cell(col, row)
        lay = self.layout
        draw.rectangle(
            (x, y + 2, x + lay.char_w - 1, y + lay.line_h - 3), fill=self.theme.accent
        )

    def _draw_shell(self, draw, lines: Sequence[Line], cursor_on: bool) -> None:
        cols, rows = self.layout.cols, self.layout.rows
        wrapped: List[List[Run]] = []
        for line in lines:
            wrapped.extend(_wrap_runs(line, cols))
        visible = wrapped[-rows:]
        end_col = 0
        for r, runs in enumerate(visible):
            end_col = self._draw_runs(draw, runs, 0, r)
        if cursor_on and visible:
            if end_col >= cols and len(visible) < rows:
                self._draw_cursor(draw, 0, len(visible))
            else:
                self._draw_cursor(draw, min(end_col, cols - 1), len(visible) - 1)

    def _draw_editor(self, draw, scene: Scene, cursor_on: bool) -> None:
        th, lay = self.theme, self.layout
        erows = lay.rows - 1
        cols = self.code_cols
        # Build wrapped rows of the typed prefix: (line number or None, start, end)
        rows: List[Tuple[Optional[int], int, int]] = []
        start = 0
        prefix = self.script[: scene.typed]
        for lineno, text in enumerate(prefix.split("\n"), 1):
            if not text:
                rows.append((lineno, start, start))
            for k in range(0, len(text), cols):
                rows.append(
                    (
                        lineno if k == 0 else None,
                        start + k,
                        start + min(k + cols, len(text)),
                    )
                )
            start += len(text) + 1
        top = max(0, len(rows) - erows)
        visible = rows[top:]
        cur_line = prefix.count("\n") + 1
        x_code = self.gutter + 1

        for r, (lineno, s, e) in enumerate(visible):
            if r == len(visible) - 1 and not scene.status_cursor:
                x, y = self._cell(0, r)
                draw.rectangle(
                    (lay.content[0] - 6, y, lay.content[2] + 6, y + lay.line_h - 1),
                    fill=self._cursor_line_bg,
                )
            if lineno is not None:
                num = str(lineno).rjust(self.gutter - 1)
                color = th.fg if lineno == cur_line else th.dim
                self._draw_runs(draw, [(num, color, False)], 0, r)
            self._draw_colored(draw, s, e, x_code, r)
        for r in range(len(visible), erows):
            self._draw_runs(draw, [("~", th.dim, False)], 0, r)

        status_row = lay.rows - 1
        end_col = self._draw_runs(draw, scene.status, 0, status_row)
        last_line = prefix.rsplit("\n", 1)[-1]
        pos = f"{cur_line},{len(last_line) + 1}"
        self._draw_runs(draw, [(pos, th.dim, False)], lay.cols - len(pos), status_row)

        if cursor_on:
            if scene.status_cursor:
                self._draw_cursor(draw, end_col, status_row)
            elif visible:
                _, s, e = visible[-1]
                self._draw_cursor(draw, x_code + (e - s), len(visible) - 1)

    def _draw_colored(self, draw, start: int, end: int, col: int, row: int) -> None:
        runs: List[Run] = []
        for k in range(start, end):
            ch, color = self.script[k], self.colors[k]
            if runs and runs[-1][1] == color:
                runs[-1] = (runs[-1][0] + ch, color, False)
            else:
                runs.append((ch, color, False))
        self._draw_runs(draw, runs, col, row)

    # ------------------------------------------------------------------ #
    def _base(self, window_title, title, subtitle, footer) -> Image.Image:
        th, lay = self.theme, self.layout
        W, H = lay.width, lay.height
        img = Image.new("RGB", (W, H), th.bg_bottom)
        draw = ImageDraw.Draw(img)
        for y in range(H):
            draw.line((0, y, W, y), fill=_mix(th.bg_top, th.bg_bottom, y / H))

        # Soft glow / shadow behind the window
        x0, y0, x1, y1 = lay.window
        radius = int(26 * lay.scale)
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).rounded_rectangle(
            (x0 - 6, y0 - 6, x1 + 6, y1 + 6), radius=radius, fill=150
        )
        glow = glow.filter(ImageFilter.GaussianBlur(int(30 * lay.scale)))
        glow_color = th.accent if th.scanlines else (0, 0, 0)
        img.paste(Image.new("RGB", (W, H), glow_color), (0, 0), glow)

        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=th.window_bg)
        draw.rounded_rectangle(
            (x0, y0, x1, y0 + lay.titlebar_h), radius=radius, fill=th.titlebar_bg
        )
        draw.rectangle(
            (x0, y0 + lay.titlebar_h - radius, x1, y0 + lay.titlebar_h),
            fill=th.titlebar_bg,
        )
        r = int(11 * lay.scale)
        cy = y0 + lay.titlebar_h // 2
        for i, color in enumerate(_TRAFFIC_LIGHTS):
            cx = x0 + int(36 * lay.scale) + i * int(36 * lay.scale)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        small = _load_font(self.title_font_path, int(24 * lay.scale))
        draw.text(
            ((x0 + x1) // 2, cy),
            window_title,
            font=small,
            fill=th.titlebar_fg,
            anchor="mm",
        )

        if title:
            self._draw_wrapped(
                draw, title, int(66 * lay.scale), th.title_fg, y0, subtitle
            )
        if footer:
            font = _load_font(self.title_font_path, int(40 * lay.scale))
            fy = (y1 + H) // 2
            draw.text((W // 2, fy), footer, font=font, fill=th.subtitle_fg, anchor="mm")
        return img

    def _draw_wrapped(self, draw, title, size, color, window_top, subtitle) -> None:
        lay = self.layout
        max_w = lay.width - 2 * int(70 * lay.scale)
        font = _load_font(self.title_font_path, size)
        lines = _wrap_words(title, font, max_w)
        # Shrink until the title block fits above the window
        sub_font = _load_font(self.title_font_path, int(size * 0.55))
        while size > 24:
            block = len(lines) * int(size * 1.15) + (int(size * 0.9) if subtitle else 0)
            if block <= window_top - int(60 * lay.scale):
                break
            size = int(size * 0.9)
            font = _load_font(self.title_font_path, size)
            sub_font = _load_font(self.title_font_path, int(size * 0.55))
            lines = _wrap_words(title, font, max_w)
        line_h = int(size * 1.15)
        block = len(lines) * line_h + (int(size * 0.9) if subtitle else 0)
        y = (window_top - block) // 2 + line_h // 2
        for line in lines:
            draw.text((lay.width // 2, y), line, font=font, fill=color, anchor="mm")
            y += line_h
        if subtitle:
            draw.text(
                (lay.width // 2, y + int(size * 0.1)),
                subtitle,
                font=sub_font,
                fill=self.theme.subtitle_fg,
                anchor="mm",
            )

    def _scanline_mask(self) -> Image.Image:
        x0, y0, x1, y1 = self.layout.content
        mask = Image.new("RGB", (x1 - x0, y1 - y0), (255, 255, 255))
        draw = ImageDraw.Draw(mask)
        step = max(3, int(4 * self.layout.scale))
        for y in range(0, y1 - y0, step):
            draw.line((0, y, x1 - x0, y), fill=(200, 200, 200))
        return mask


def _wrap_words(text: str, font, max_w: int) -> List[str]:
    """Wrap to the fewest lines, then narrow the width to balance them."""
    lines = _greedy_wrap(text, font, max_w)
    lo, hi = max_w // 3, max_w
    while lo < hi:
        mid = (lo + hi) // 2
        if len(_greedy_wrap(text, font, mid)) == len(lines):
            hi = mid
        else:
            lo = mid + 1
    return _greedy_wrap(text, font, hi)


def _greedy_wrap(text: str, font, max_w: int) -> List[str]:
    lines: List[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            if font.getlength(trial) <= max_w or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines
