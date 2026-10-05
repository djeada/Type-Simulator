"""Draws reel frames with Pillow."""

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from type_simulator.reel.terminal import Line, Run
from type_simulator.reel.themes import RGB, Theme
from type_simulator.reel.timeline import BROWSER, EDITOR, Scene

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

FULL_BLOCK = "\u2588"
_BLOCK_SPLIT_RE = re.compile(f"{FULL_BLOCK}+|[^{FULL_BLOCK}]+")

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
    # Second window under the editor (live document preview), if any
    preview: Optional[Tuple[int, int, int, int]] = None


def compute_layout(
    width: int,
    height: int,
    font_size: Optional[int],
    mono_path: Optional[str],
    split: bool = False,
) -> Layout:
    """Window geometry; `split` stacks the editor above a preview window."""
    scale = width / 1080
    portrait = height >= width
    side = int(54 * scale)
    preview = None
    if split and portrait:
        top, bottom = int(height * 0.15), int(height * 0.525)
        preview = (side, int(height * 0.545), width - side, int(height * 0.905))
    elif split:
        # Side by side: editor left, preview right
        top, bottom = int(height * 0.2), int(height * 0.9)
        mid = width // 2
        preview = (mid + side // 4, top, width - side, bottom)
        width_editor = mid - side // 4
    elif portrait:
        top, bottom = int(height * 0.19), int(height * 0.86)
    else:
        top, bottom = int(height * 0.2), int(height * 0.9)
    right = width_editor if split and not portrait else width - side
    window = (side, top, right, bottom)
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
        preview,
    )


def preview_viewport(layout: Layout) -> Tuple[int, int, int, int]:
    """Box of the document area inside the preview window."""
    x0, y0, x1, y1 = layout.preview
    return (x0, y0 + layout.titlebar_h, x1, y1)


def browser_chrome_heights(layout: Layout) -> Tuple[int, int]:
    """Heights of the browser's tab strip and toolbar."""
    return int(58 * layout.scale), int(62 * layout.scale)


def browser_viewport(layout: Layout) -> Tuple[int, int, int, int]:
    """Box of the page area inside the browser window."""
    x0, y0, x1, y1 = layout.window
    tabs, toolbar = browser_chrome_heights(layout)
    return (x0, y0 + tabs + toolbar, x1, y1)


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
        ui_font_path: Optional[str] = None,
        capture=None,
        url: Optional[str] = None,
        latex=None,
        preview_title: Optional[str] = None,
    ):
        self.theme = theme
        self.layout = layout
        self.script = script
        self.colors = colors
        self.filename = filename
        self.font = _load_font(mono_path, layout.font_size)
        self.font_bold = _load_font(mono_bold_path or mono_path, layout.font_size)
        self.title_font_path = title_font_path
        self.ui_font_path = ui_font_path or title_font_path
        self.capture = capture
        self.latex = latex
        self.preview_title = preview_title or "Preview"
        total_lines = script.count("\n") + 1
        self.gutter = len(str(total_lines)) + 1
        self.code_cols = layout.cols - self.gutter - 1
        self._bases = {
            "shell": self._base(f"{theme.prompt}: ~", title, subtitle, footer),
            EDITOR: self._base(f"{filename} - vim", title, subtitle, footer),
        }
        if capture is not None:
            page = (capture.title or filename, url or filename)
            self._bases[BROWSER] = self._base(page[0], title, subtitle, footer, page)
            self._page_mask = self._window_mask().crop(browser_viewport(layout))
        if latex is not None and layout.preview:
            box = preview_viewport(layout)
            self._doc_mask = self._window_mask(layout.preview).crop(box)
        self._scanlines = self._scanline_mask() if theme.scanlines else None
        self._cursor_line_bg = _mix(theme.window_bg, theme.fg, 0.07)

    # ------------------------------------------------------------------ #
    def render(self, scene: Scene, cursor_on: bool) -> Image.Image:
        img = self._bases[scene.mode].copy()
        if scene.mode == BROWSER:
            box = browser_viewport(self.layout)
            img.paste(self.capture.frame(scene.frame), box[:2], self._page_mask)
            return img
        draw = ImageDraw.Draw(img)
        if scene.mode == EDITOR:
            self._draw_editor(draw, scene, cursor_on)
        else:
            self._draw_shell(draw, scene.shell, cursor_on)
        if self._scanlines is not None:
            box = self.layout.content
            region = img.crop(box)
            img.paste(ImageChops.multiply(region, self._scanlines), box[:2])
        if self.latex is not None and self.layout.preview:
            self._draw_document(img, draw, scene.preview)
        return img

    def _draw_document(self, img, draw, index: int) -> None:
        """Paste the live document preview and its page indicator."""
        box = preview_viewport(self.layout)
        img.paste(self.latex.image(index), box[:2], self._doc_mask)
        label = self.latex.label(index)
        if label:
            x0, y0, x1, _ = self.layout.preview
            font = _load_font(self.ui_font_path, int(22 * self.layout.scale))
            draw.text(
                (x1 - int(26 * self.layout.scale), y0 + self.layout.titlebar_h // 2),
                label,
                font=font,
                fill=self.theme.titlebar_fg,
                anchor="rm",
            )

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
            fill = color or self.theme.fg
            font = self.font_bold if bold else self.font
            if FULL_BLOCK not in text:
                draw.text(self._cell(col, row), text, font=font, fill=fill)
            else:
                # Full blocks become solid cells, so pixel art has no seams
                for m in _BLOCK_SPLIT_RE.finditer(text):
                    start = col + m.start()
                    if m.group()[0] == FULL_BLOCK:
                        x0, y0 = self._cell(start, row)
                        x1, _ = self._cell(start + len(m.group()), row)
                        draw.rectangle(
                            (x0, y0, x1 - 1, y0 + self.layout.line_h - 1), fill=fill
                        )
                    elif m.group().strip():
                        draw.text(
                            self._cell(start, row), m.group(), font=font, fill=fill
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
    def _base(self, window_title, title, subtitle, footer, page=None) -> Image.Image:
        """Background, titles and window; `page` = (tab title, url) for a browser."""
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
        if lay.preview and self.latex is not None:
            self._draw_preview_window(img)

        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=th.window_bg)
        if page:
            self._draw_browser_chrome(draw, *page)
            self._draw_texts(draw, title, subtitle, footer)
            return img
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

        self._draw_texts(draw, title, subtitle, footer)
        return img

    def _draw_texts(self, draw, title, subtitle, footer) -> None:
        th, lay = self.theme, self.layout
        x0, y0, x1, y1 = lay.window
        if lay.preview:
            y1 = max(y1, lay.preview[3])
        if title:
            self._draw_wrapped(
                draw, title, int(66 * lay.scale), th.title_fg, y0, subtitle
            )
        if footer:
            font = _load_font(self.title_font_path, int(40 * lay.scale))
            fy = (y1 + lay.height) // 2
            draw.text(
                (lay.width // 2, fy),
                footer,
                font=font,
                fill=th.subtitle_fg,
                anchor="mm",
            )

    def _draw_browser_chrome(self, draw, tab_title: str, url: str) -> None:
        """Tab strip and toolbar of a browser window, in the theme's colors."""
        th, lay = self.theme, self.layout
        s = lay.scale
        x0, y0, x1, _ = lay.window
        tabs_h, bar_h = browser_chrome_heights(lay)
        radius = int(26 * s)
        strip = th.titlebar_bg
        active = _mix(th.window_bg, th.fg, 0.1)
        top = y0 + tabs_h + bar_h
        draw.rounded_rectangle((x0, y0, x1, top), radius=radius, fill=strip)
        draw.rectangle((x0, y0 + tabs_h, x1, top), fill=active)

        r, cy = int(11 * s), y0 + tabs_h // 2 + int(3 * s)
        for i, color in enumerate(_TRAFFIC_LIGHTS):
            cx = x0 + int(36 * s) + i * int(36 * s)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)

        # Active tab with favicon, title and close button, then a "+"
        font = _load_font(self.ui_font_path, int(23 * s))
        tx0, tx1 = x0 + int(140 * s), x0 + int(560 * s)
        draw.rounded_rectangle(
            (tx0, y0 + int(9 * s), tx1, y0 + tabs_h + radius),
            radius=int(14 * s),
            fill=active,
        )
        fav = int(9 * s)
        fx = tx0 + int(28 * s)
        draw.ellipse((fx - fav, cy - fav, fx + fav, cy + fav), fill=th.accent)
        max_w = tx1 - tx0 - int(100 * s)
        label = tab_title
        while label and font.getlength(label) > max_w:
            label = label[:-2] + "…"
        draw.text((fx + int(24 * s), cy), label, font=font, fill=th.fg, anchor="lm")
        draw.text(
            (tx1 - int(28 * s), cy), "×", font=font, fill=th.titlebar_fg, anchor="mm"
        )
        plus = _load_font(self.ui_font_path, int(32 * s))
        draw.text(
            (tx1 + int(34 * s), cy), "+", font=plus, fill=th.titlebar_fg, anchor="mm"
        )

        # Toolbar: navigation buttons and the address bar
        by = y0 + tabs_h + bar_h // 2
        self._draw_nav_icons(draw, x0 + int(38 * s), by, int(50 * s), th.titlebar_fg)
        ux0, ux1 = x0 + int(190 * s), x1 - int(28 * s)
        half = int(22 * s)
        draw.rounded_rectangle(
            (ux0, by - half, ux1, by + half), radius=half, fill=th.window_bg
        )
        head, _, tail = url.rpartition("/")
        x = ux0 + int(22 * s)
        url_font = _load_font(self.ui_font_path, int(22 * s))
        if head:
            draw.text((x, by), head + "/", font=url_font, fill=th.dim, anchor="lm")
            x += int(url_font.getlength(head + "/"))
        draw.text((x, by), tail, font=url_font, fill=th.fg, anchor="lm")

    def _draw_nav_icons(self, draw, x: int, y: int, step: int, color) -> None:
        """Back, forward and reload buttons drawn as shapes (fonts may lack them)."""
        s = self.layout.scale
        r, w = int(11 * s), max(2, int(3 * s))
        for i, direction in enumerate((-1, 1)):
            cx = x + i * step
            tip, tail = cx + direction * r, cx - direction * r
            draw.line((tail, y, tip, y), fill=color, width=w)
            for dy in (-1, 1):
                draw.line(
                    (tip, y, tip - direction * r * 0.7, y + dy * r * 0.7),
                    fill=color,
                    width=w,
                )
        cx = x + 2 * step
        draw.arc(
            (cx - r, y - r, cx + r, y + r), start=-60, end=250, fill=color, width=w
        )
        hx, hy = cx + r * 0.5, y - r * 0.87  # arrow head at the open end of the arc
        draw.polygon(
            [
                (hx + 5 * s, hy - 1 * s),
                (hx - 4 * s, hy - 6 * s),
                (hx - 3 * s, hy + 5 * s),
            ],
            fill=color,
        )

    def _window_mask(self, rect=None) -> Image.Image:
        lay = self.layout
        mask = Image.new("L", (lay.width, lay.height), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            rect or lay.window, radius=int(26 * lay.scale), fill=255
        )
        return mask

    def _draw_preview_window(self, img: Image.Image) -> None:
        """Second window, a document viewer, below (or beside) the editor."""
        th, lay = self.theme, self.layout
        x0, y0, x1, y1 = lay.preview
        s = lay.scale
        radius = int(26 * s)
        glow = Image.new("L", img.size, 0)
        ImageDraw.Draw(glow).rounded_rectangle(
            (x0 - 6, y0 - 6, x1 + 6, y1 + 6), radius=radius, fill=150
        )
        glow = glow.filter(ImageFilter.GaussianBlur(int(30 * s)))
        glow_color = th.accent if th.scanlines else (0, 0, 0)
        img.paste(Image.new("RGB", img.size, glow_color), (0, 0), glow)
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=(255, 255, 255))
        draw.rounded_rectangle(
            (x0, y0, x1, y0 + lay.titlebar_h), radius=radius, fill=th.titlebar_bg
        )
        draw.rectangle(
            (x0, y0 + lay.titlebar_h - radius, x1, y0 + lay.titlebar_h),
            fill=th.titlebar_bg,
        )
        r, cy = int(11 * s), y0 + lay.titlebar_h // 2
        for i, color in enumerate(_TRAFFIC_LIGHTS):
            cx = x0 + int(36 * s) + i * int(36 * s)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        font = _load_font(self.title_font_path, int(24 * s))
        draw.text(
            ((x0 + x1) // 2, cy),
            self.preview_title,
            font=font,
            fill=th.titlebar_fg,
            anchor="mm",
        )

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
