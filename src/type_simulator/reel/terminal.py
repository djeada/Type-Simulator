"""
Minimal terminal emulation for reels.

Turns program output (including ANSI colors, carriage-return progress bars and
clear-screen sequences) into styled lines that the renderer can draw.
"""

import re
from typing import List, Optional, Tuple

from type_simulator.reel.themes import RGB

# A run of text sharing one style: (text, color or None for default fg, bold)
Run = Tuple[str, Optional[RGB], bool]
Line = Tuple[Run, ...]

_CSI_RE = re.compile(r"\x1b\[([0-9;?]*)([@-~])")
# Sequences that start redrawing the whole screen (full-screen animations)
SCREEN_RESET_RE = re.compile(r"\x1b\[(?:[0-3]?J|(?:1;1|0;0)?[Hf])")
_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
TAB_WIDTH = 4


def _xterm_256(n: int, palette: List[RGB]) -> RGB:
    if n < 16:
        return palette[n]
    if n < 232:
        n -= 16
        levels = [0, 95, 135, 175, 215, 255]
        return (levels[n // 36], levels[(n // 6) % 6], levels[n % 6])
    gray = 8 + (n - 232) * 10
    return (gray, gray, gray)


class TerminalBuffer:
    """Accumulates styled lines; the last line is the one being written."""

    def __init__(self, palette: List[RGB]):
        self.palette = palette
        self.lines: List[List[Run]] = [[]]
        self._color: Optional[RGB] = None
        self._color_index: Optional[int] = None
        self._bold = False
        self._pending_cr = False
        self._partial_escape = ""

    # ------------------------------------------------------------------ #
    def write(self, text: str, color: Optional[RGB] = None, bold: bool = False):
        """Write literal text (no escape processing) in a fixed style."""
        for i, part in enumerate(text.split("\n")):
            if i:
                self.newline()
            if part:
                self._append(part, color, bold)

    def newline(self) -> None:
        self._pending_cr = False
        self.lines.append([])

    def clear(self) -> None:
        self.lines = [[]]
        self._pending_cr = False

    def feed(self, data: str) -> None:
        """Feed raw program output, interpreting ANSI escapes, CR and LF."""
        data = self._partial_escape + data
        self._partial_escape = ""
        # Keep an incomplete trailing escape sequence for the next chunk
        esc = data.rfind("\x1b")
        if esc != -1 and not _CSI_RE.match(data, esc) and not _OSC_RE.match(data, esc):
            if len(data) - esc < 32:
                self._partial_escape = data[esc:]
                data = data[:esc]

        data = _OSC_RE.sub("", data)
        pos = 0
        for m in _CSI_RE.finditer(data):
            self._feed_text(data[pos : m.start()])
            self._handle_csi(m.group(1), m.group(2))
            pos = m.end()
        self._feed_text(data[pos:])

    def snapshot(self, keep: int) -> Tuple[Line, ...]:
        """Immutable copy of the last `keep` lines."""
        return tuple(tuple(line) for line in self.lines[-keep:])

    # ------------------------------------------------------------------ #
    def _feed_text(self, text: str) -> None:
        buf = []
        for ch in text:
            if ch == "\n":
                self._flush(buf)
                self.newline()
            elif ch == "\r":
                self._flush(buf)
                self._pending_cr = True
            elif ch == "\t":
                col = sum(len(r[0]) for r in self.lines[-1]) + len(buf)
                buf.append(" " * (TAB_WIDTH - col % TAB_WIDTH))
            elif ch == "\b":
                self._flush(buf)
                self._backspace()
            elif ch >= " ":
                buf.append(ch)
            # Other control characters (including stray ESC) are dropped
        self._flush(buf)

    def _flush(self, buf: List[str]) -> None:
        if buf:
            self._append("".join(buf), self._color, self._bold)
            buf.clear()

    def _append(self, text: str, color: Optional[RGB], bold: bool) -> None:
        if self._pending_cr:
            # Carriage return followed by text: redraw the line (progress bars)
            self.lines[-1] = []
            self._pending_cr = False
        line = self.lines[-1]
        if line and line[-1][1] == color and line[-1][2] == bold:
            line[-1] = (line[-1][0] + text, color, bold)
        else:
            line.append((text, color, bold))

    def _backspace(self) -> None:
        line = self.lines[-1]
        if line:
            text, color, bold = line[-1]
            if len(text) > 1:
                line[-1] = (text[:-1], color, bold)
            else:
                line.pop()

    def _handle_csi(self, params: str, final: str) -> None:
        if final == "m":
            self._handle_sgr(params)
        elif final == "J" and params in ("2", "3"):
            self.clear()
        elif final in "Hf" and params in ("", "1;1", "0;0"):
            # Cursor home: animations redraw from the top, so start a fresh screen
            self.clear()
        elif final == "K":
            # Erase line: treat as clearing the current line
            self.lines[-1] = []
        # Cursor movement and other sequences are ignored

    def _handle_sgr(self, params: str) -> None:
        codes = [int(c) if c.isdigit() else 0 for c in params.split(";")] or [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                self._color = self._color_index = None
                self._bold = False
            elif c == 1:
                self._bold = True
                if self._color_index is not None and self._color_index < 8:
                    self._color = self.palette[self._color_index + 8]
            elif c == 22:
                self._bold = False
            elif 30 <= c <= 37:
                self._color_index = c - 30
                idx = self._color_index + (8 if self._bold else 0)
                self._color = self.palette[idx]
            elif 90 <= c <= 97:
                self._color_index = c - 90 + 8
                self._color = self.palette[self._color_index]
            elif c == 39:
                self._color = self._color_index = None
            elif c in (38, 48):
                # Extended color: 5;n or 2;r;g;b. Backgrounds are skipped.
                mode = codes[i + 1] if i + 1 < len(codes) else None
                if mode == 5 and i + 2 < len(codes):
                    if c == 38:
                        self._color = _xterm_256(codes[i + 2], self.palette)
                        self._color_index = None
                    i += 2
                elif mode == 2 and i + 4 < len(codes):
                    if c == 38:
                        self._color = tuple(codes[i + 2 : i + 5])  # type: ignore
                        self._color_index = None
                    i += 4
            i += 1
