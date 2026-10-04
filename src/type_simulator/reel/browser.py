"""
Capture a web page as a sequence of frames for reels.

The page is loaded in headless Chromium (via Playwright) with a paused fake
clock. Time is advanced exactly one video frame between screenshots, so
requestAnimationFrame/timer driven animations are recorded frame-perfectly
regardless of how long each screenshot takes.
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

BROWSER_EXTENSIONS = {".html", ".htm", ".svg"}
INSTALL_HINT = (
    "Browser reels need Playwright: pip install playwright && "
    "python -m playwright install chromium-headless-shell"
)


@dataclass
class PageCapture:
    frames_dir: Path
    count: int
    fps: int
    size: Tuple[int, int]
    title: str = ""
    console_errors: List[str] = field(default_factory=list)

    def path(self, index: int) -> Path:
        index = max(0, min(self.count - 1, index))
        return self.frames_dir / f"{index:05d}.jpg"

    def frame(self, index: int) -> Image.Image:
        return _load(self.path(index))


@lru_cache(maxsize=4)
def _load(path: Path) -> Image.Image:
    with Image.open(path) as img:
        return img.convert("RGB")


def playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def capture_page(
    page: Path,
    size: Tuple[int, int],
    fps: int,
    duration: float,
    out_dir: Path,
    zoom: float = 1.0,
) -> PageCapture:
    """
    Record `duration` seconds of `page` at `fps` into JPEG frames of exactly
    `size` pixels. `zoom` > 1 makes the page render larger (like browser zoom),
    which also gives it a smaller CSS viewport.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(INSTALL_HINT) from None

    width, height = size
    count = max(1, round(duration * fps))
    out_dir.mkdir(parents=True, exist_ok=True)
    capture = PageCapture(out_dir, count, fps, size)
    viewport = {"width": round(width / zoom), "height": round(height / zoom)}
    logger.info(
        "Capturing %s: %d frames at %dfps, viewport %dx%d CSS px",
        page.name,
        count,
        fps,
        viewport["width"],
        viewport["height"],
    )

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except PlaywrightError as e:
            raise RuntimeError(f"Could not start Chromium ({e}). {INSTALL_HINT}") from e
        try:
            context = browser.new_context(viewport=viewport, device_scale_factor=zoom)
            tab = context.new_page()
            tab.on(
                "console",
                lambda msg: msg.type == "error"
                and capture.console_errors.append(msg.text),
            )
            tab.on("pageerror", lambda err: capture.console_errors.append(str(err)))
            # Freeze time; it only moves when we advance it below
            tab.clock.install(time=0)
            tab.clock.pause_at(1000)
            tab.goto(page.resolve().as_uri(), wait_until="load")
            capture.title = tab.title() or page.name
            elapsed_ms = 0
            for i in range(count):
                target = round((i + 1) * 1000 / fps)
                tab.clock.run_for(target - elapsed_ms)
                elapsed_ms = target
                tab.screenshot(path=str(capture.path(i)), type="jpeg", quality=95)
        finally:
            browser.close()

    for error in capture.console_errors[:5]:
        logger.warning("Page error: %s", error)
    # Screenshots can be off by a pixel with fractional zoom; normalize them
    with Image.open(capture.path(0)) as first:
        mismatch = first.size != size
    if mismatch:
        for i in range(count):
            path = capture.path(i)
            with Image.open(path) as img:
                fixed = img.convert("RGB").resize(size)
            fixed.save(path, quality=95)
    return capture
