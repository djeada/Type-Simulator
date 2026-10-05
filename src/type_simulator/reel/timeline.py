"""
Builds the reel's storyboard: a list of timestamped scenes plus the moments
keys are pressed (for click sounds).

The story is: a shell prompt types `vim <file>`, the script is typed into the
editor, saved with `:wq`, run from the shell, and its output scrolls by.
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from type_simulator.reel.terminal import (
    SCREEN_RESET_RE,
    Line,
    Run,
    TerminalBuffer,
)
from type_simulator.reel.themes import RGB, Theme

SHELL = "shell"
EDITOR = "editor"
BROWSER = "browser"


@dataclass(frozen=True)
class Scene:
    mode: str
    shell: Tuple[Line, ...] = ()
    typed: int = 0  # editor: number of script characters typed so far
    status: Tuple[Run, ...] = ()  # editor: bottom status line
    status_cursor: bool = False  # editor: cursor sits in the status line
    frame: int = -1  # browser: index of the captured page frame
    preview: int = -1  # live document preview: snapshot index (-1 = blank)


@dataclass
class Timeline:
    keyframes: List[Tuple[float, Scene]] = field(default_factory=list)
    # (time, kind) with kind in {"key", "space", "enter"}
    sounds: List[Tuple[float, str]] = field(default_factory=list)
    duration: float = 0.0
    typing_time: float = 0.0  # seconds spent typing the script itself


@dataclass
class Pacing:
    speed: float = 0.045
    variance: float = 0.025
    pause_probability: float = 0.08
    pause_duration: float = 0.25
    scale: float = 1.0  # multiplies script typing time (used to fit a duration)
    intro: float = 0.8
    end_hold: float = 2.5
    line_delay: float = 0.05  # minimum gap between output lines
    max_output_gap: float = 1.5  # long sleeps in the script are shortened to this


class TimelineBuilder:
    def __init__(
        self,
        theme: Theme,
        pacing: Pacing,
        rows: int,
        seed: Optional[int] = None,
        preview_checkpoints: Sequence[Tuple[int, int]] = (),
        preview_delay: float = 0.4,
    ):
        """
        `preview_checkpoints` are (characters typed, snapshot) pairs for a live
        document preview, which updates `preview_delay` seconds after the
        checkpoint is typed, like a recompile would.
        """
        self.theme = theme
        self.pacing = pacing
        self.rows = rows
        self.rng = random.Random(seed)
        self.t = 0.0
        self.timeline = Timeline()
        self.term = TerminalBuffer(theme.ansi)
        self.checkpoints = list(preview_checkpoints)
        self.preview_delay = preview_delay
        self.preview = -1
        self._pending: List[Tuple[float, int]] = []

    # ------------------------------------------------------------------ #
    def build(
        self,
        script: str,
        filename: str,
        run_command: Optional[str],
        output_chunks: Optional[Sequence[Tuple[float, str]]],
        timed_out: bool = False,
        browser_command: Optional[str] = None,
        browser_frames: int = 0,
        browser_fps: int = 30,
    ) -> Timeline:
        """
        With `browser_command`, the saved file is opened in a browser instead
        of being run: the reel cuts to `browser_frames` captured page frames,
        which also cover the closing hold.
        """
        p = self.pacing
        self._prompt()
        self._emit_shell()
        self.t += p.intro

        self._type_shell(f"vim {filename}", speed_factor=0.8)
        self._press_enter()
        self.t += 0.35

        # Editor: open a new file and type the script
        status_new = ((f'"{filename}" [New]', self.theme.dim, False),)
        insert = (("-- INSERT --", self.theme.fg, True),)
        self._emit_editor(0, status_new)
        self.t += 0.6
        self._emit_editor(0, insert)
        start = self.t
        self._type_editor(script, insert)
        self.timeline.typing_time = self.t - start

        # Save and quit
        self.t += 0.5
        self._emit_editor(len(script), (), status_cursor=True)
        typed = ""
        for ch in ":wq":
            self.t += self._interval(ch, 1.3)
            typed += ch
            self._emit_editor(len(script), ((typed, self.theme.fg, False),), True)
            self._sound("key")
        self._sound("enter", self.t + 0.12)
        self.t += 0.12
        lines = script.count("\n") + (0 if script.endswith("\n") else 1)
        written = f'"{filename}" {lines}L, {len(script.encode())}B written'
        self._emit_editor(len(script), ((written, self.theme.fg, False),))
        self.t += 0.6

        # Back to the shell (the line after `vim <file>` is still empty)
        self._prompt()
        self._emit_shell()
        if run_command:
            self.t += 0.5
            self._type_shell(run_command)
            self._press_enter()
            self._play_output(output_chunks or [])
            if timed_out:
                self.term.write("^C", self.theme.dim)
            if self.term.lines[-1]:
                self.term.newline()
            self.t += 0.3
            self._prompt()
            self._emit_shell()

        if browser_command and browser_frames:
            self.t += 0.5
            self._type_shell(browser_command)
            self._press_enter()
            self.t += 0.4  # the browser window opening
            start = self.t
            for i in range(browser_frames):
                self.t = start + i / browser_fps
                self.timeline.keyframes.append((self.t, Scene(BROWSER, frame=i)))
            self.t = start + browser_frames / browser_fps
        else:
            self.t += p.end_hold
        self.timeline.duration = self.t
        return self.timeline

    # ------------------------------------------------------------------ #
    def _prompt(self) -> None:
        th = self.theme
        user = th.prompt
        self.term.write(user, th.accent, True)
        self.term.write(":", th.fg)
        self.term.write("~", th.path, True)
        self.term.write("# " if user.startswith("root") else "$ ", th.fg)

    def _emit_shell(self) -> None:
        self._sync_preview()
        scene = Scene(SHELL, shell=self.term.snapshot(self.rows), preview=self.preview)
        self.timeline.keyframes.append((self.t, scene))

    def _emit_editor(self, typed: int, status, status_cursor: bool = False) -> None:
        self._sync_preview()
        scene = Scene(
            EDITOR,
            typed=typed,
            status=status,
            status_cursor=status_cursor,
            preview=self.preview,
        )
        self.timeline.keyframes.append((self.t, scene))

    def _sync_preview(self) -> None:
        while self._pending and self._pending[0][0] <= self.t:
            self.preview = self._pending.pop(0)[1]

    def _reach(self, typed: int) -> None:
        """Schedule preview updates for checkpoints up to `typed` characters."""
        while self.checkpoints and self.checkpoints[0][0] <= typed:
            _, snapshot = self.checkpoints.pop(0)
            self._pending.append((self.t + self.preview_delay, snapshot))

    def _sound(self, kind: str, at: Optional[float] = None) -> None:
        self.timeline.sounds.append((self.t if at is None else at, kind))

    def _interval(self, ch: str, factor: float = 1.0) -> float:
        p = self.pacing
        base = p.speed + p.variance * (2 * self.rng.random() - 1)
        interval = max(0.012, base) * factor
        if ch == " " and self.rng.random() < p.pause_probability:
            interval += p.pause_duration * self.rng.uniform(0.5, 1.5) * factor
        return interval

    def _type_shell(self, text: str, speed_factor: float = 1.0) -> None:
        for ch in text:
            self.t += self._interval(ch, speed_factor)
            self.term.write(ch, self.theme.fg)
            self._emit_shell()
            self._sound("space" if ch == " " else "key")

    def _press_enter(self) -> None:
        self.t += 0.15
        self._sound("enter")
        self.term.newline()
        self._emit_shell()

    def _type_editor(self, script: str, status) -> None:
        scale = self.pacing.scale
        i, n = 0, len(script)
        while i < n:
            ch = script[i]
            self.t += self._interval(ch, scale)
            i += 1
            if ch == "\n":
                self._sound("enter")
                # Brief "thinking" pause at line ends, then auto-indent
                self.t += self.rng.uniform(0.05, 0.2) * scale
                while i < n and script[i] in " \t":
                    i += 1
            else:
                self._sound("space" if ch == " " else "key")
            self._reach(i)
            self._emit_editor(i, status)

    def _play_output(self, chunks: Sequence[Tuple[float, str]]) -> None:
        p = self.pacing
        prev = 0.0
        frame_mode = False
        for real_t, text in chunks:
            gap = max(0.0, real_t - prev)
            if frame_mode and gap > 0.015:
                # The program paused, so what it printed so far is complete
                self._emit_shell()
            self.t += min(gap, p.max_output_gap)
            prev = real_t
            if frame_mode or SCREEN_RESET_RE.search(text):
                # Full-screen animation: show each frame once it is complete,
                # i.e. right before the next redraw starts, at real speed
                frame_mode = True
                self._play_frames(text)
                continue
            pieces = text.split("\n")
            for k, piece in enumerate(pieces):
                last = k == len(pieces) - 1
                self.term.feed(piece if last else piece + "\n")
                if piece or not last:
                    self._emit_shell()
                if not last:
                    self.t += p.line_delay
        if frame_mode:
            self._emit_shell()

    def _play_frames(self, text: str) -> None:
        pos = 0
        for m in SCREEN_RESET_RE.finditer(text):
            self.term.feed(text[pos : m.start()])
            if any(self.term.lines[-self.rows :]):
                self._emit_shell()
            self.term.feed(m.group(0))
            pos = m.end()
        # The rest may be a partial frame; it is shown at the next boundary
        self.term.feed(text[pos:])


def fit_scale(timeline: Timeline, target: float, current_scale: float) -> float:
    """Typing scale that makes the reel last roughly `target` seconds."""
    fixed = timeline.duration - timeline.typing_time
    if timeline.typing_time <= 0:
        return current_scale
    wanted = max(1.0, target - fixed)
    return max(0.1, min(4.0, current_scale * wanted / timeline.typing_time))


def colorize(script: str, filename: str, theme: Theme) -> List[Optional[RGB]]:
    """Per-character syntax colors for the script (None = default fg)."""
    colors: List[Optional[RGB]] = [None] * len(script)
    try:
        from pygments.lexers import get_lexer_for_filename, guess_lexer
        from pygments.util import ClassNotFound
    except ImportError:
        return colors
    try:
        lexer = get_lexer_for_filename(filename, stripnl=False, ensurenl=False)
    except ClassNotFound:
        try:
            lexer = guess_lexer(script, stripnl=False, ensurenl=False)
        except ClassNotFound:
            return colors

    pos = 0
    for ttype, value in lexer.get_tokens(script):
        color = _token_color(ttype, theme)
        end = min(pos + len(value), len(script))
        if color is not None:
            for k in range(pos, end):
                colors[k] = color
        pos = end
    return colors


def _token_color(ttype, theme: Theme) -> Optional[RGB]:
    while ttype is not None:
        name = str(ttype)[len("Token.") :] if str(ttype) != "Token" else ""
        if name in theme.syntax:
            return theme.syntax[name]
        # Pygments nests strings and numbers under Literal
        if name.startswith("Literal."):
            short = name[len("Literal.") :]
            if short in theme.syntax:
                return theme.syntax[short]
        ttype = ttype.parent
    return None
