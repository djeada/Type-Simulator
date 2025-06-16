from __future__ import annotations

import os, re, sys, time, random, shutil, logging, subprocess, argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, Sequence

# ───────────────────────────── Logging ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ───────────────────────── Config object ───────────────────────────
@dataclass
class TypistConfig:
    # Characters that often need special handling in terminal shells, etc.
    problematic_chars: set[str] = field(
        default_factory=lambda: set(":<>?|@#{}")
    )

    # Ordered list of paste targets and the hot-key to invoke them.
    # The first one that succeeds is used.
    paste_candidates: Sequence[tuple[str, Sequence[str]]] = field(
        default_factory=lambda: (
            ("primary", ("shift", "insert")),  # X11 PRIMARY + Shift-Ins
        )
    )
    paste_settle: float = 0.12                        # Wait after hot-key (s)

    typing_speed: float    = 0.05                     # Average delay per char
    typing_variance: float = 0.02                     # ± jitter on each delay


# ─────────────────────────── Token types ───────────────────────────
class Token(ABC):
    @abstractmethod
    def execute(self, executor: "Typist") -> None: ...


class TextToken(Token):
    """Emit characters, with smart fall-back for problematic ones."""

    def __init__(self, text: str):
        self.text = text

    # ---- internal helpers -------------------------------------------------
    @staticmethod
    def _copy_to_primary_x11(text: str) -> bool:
        """Copy to X11 PRIMARY selection if xclip/xsel are available."""
        for tool, args in (
            ("xclip", ["xclip", "-selection", "primary"]),
            ("xsel",  ["xsel",  "--primary", "--input"]),
        ):
            if shutil.which(tool):
                try:
                    proc = subprocess.Popen(args, stdin=subprocess.PIPE)
                    proc.communicate(input=text.encode())
                    return proc.returncode == 0
                except Exception:
                    pass
        return False

    @staticmethod
    def _type_unicode_linux(ch: str, backend):
        """Layout-agnostic Unicode input: Ctrl+Shift+U, hex, Space."""
        hexcode = format(ord(ch), "x")
        backend.hotkey("ctrl", "shift", "u")
        time.sleep(0.05)
        backend.write(hexcode)
        backend.press("space")
        time.sleep(0.05)

    # ---- main API ---------------------------------------------------------
    def execute(self, executor: "Typist") -> None:
        cfg = executor.config
        for ch in self.text:
            interval = max(
                0.0,
                cfg.typing_speed
                + cfg.typing_variance * (2 * random.random() - 1),
            )

            if ch in cfg.problematic_chars:
                # Try configured paste routes (only "primary" by default)
                pasted = False
                for target, hotkey in cfg.paste_candidates:
                    if target == "primary":
                        if self._copy_to_primary_x11(ch):
                            logger.debug("Pasting %r via PRIMARY", ch)
                            try:
                                executor.backend.hotkey(*hotkey)
                                time.sleep(cfg.paste_settle)
                                pasted = True
                                break
                            except Exception as e:
                                logger.debug("Shift-Insert failed: %s", e)
                    else:
                        logger.debug("Skipping unsupported paste target %s",
                                     target)
                if pasted:
                    continue

                # Fall-back routes
                if sys.platform.startswith("linux"):
                    logger.debug("Typing %r via Unicode hex input", ch)
                    self._type_unicode_linux(ch, executor.backend)
                elif executor.pynput:
                    logger.debug("Typing %r via pynput", ch)
                    executor.pynput.type(ch)
                    time.sleep(0.02)
                else:
                    logger.debug("Typing %r via write()", ch)
                    executor.backend.write(ch, interval=interval)
                continue  # problem char handled

            # Ordinary character
            executor.backend.write(ch, interval=interval)


class WaitToken(Token):
    def __init__(self, seconds: float):
        self.seconds = seconds

    def execute(self, executor: "Typist") -> None:
        logger.debug("Waiting %.3f s", self.seconds)
        time.sleep(self.seconds)


class KeyToken(Token):
    def __init__(self, keys: Sequence[str]):
        self.keys = keys

    def execute(self, executor: "Typist") -> None:
        logger.debug("Hot-key %s", "+".join(self.keys))
        executor.backend.hotkey(*self.keys)


class MouseMoveToken(Token):
    def __init__(self, x: int, y: int, duration: float = 0.0):
        self.x, self.y, self.duration = x, y, duration

    def execute(self, executor: "Typist") -> None:
        logger.debug("Mouse move to (%d,%d)", self.x, self.y)
        executor.backend.moveTo(self.x, self.y, duration=self.duration)


class MouseClickToken(Token):
    def __init__(self, btn: str = "left", clicks: int = 1, interval: float = 0):
        self.btn, self.clicks, self.interval = btn, clicks, interval

    def execute(self, executor: "Typist") -> None:
        logger.debug("Mouse click %s ×%d", self.btn, self.clicks)
        executor.backend.click(
            button=self.btn, clicks=self.clicks, interval=self.interval
        )


# ───────────────────────────── Parser ──────────────────────────────
class CommandParser:
    _RE_WAIT = re.compile(r"^WAIT_(\d+(?:\.\d+)?)$")
    _RE_SPEC = re.compile(r"<([^>]+)>")

    def __init__(self, strict: bool = False):
        self.strict = strict

    def parse(self, text: str) -> list[Token]:
        out: list[Token] = []
        buf: list[str]  = []
        i = 0

        def flush():
            if buf:
                out.append(TextToken("".join(buf)))
                buf.clear()

        while i < len(text):
            # Escaped braces or backslash
            if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in "{}\\":
                buf.append(text[i + 1])
                i += 2
                continue

            # Macro sequence {...}
            if text[i] == "{":
                flush()
                end = text.find("}", i)
                if end < 0:
                    if not self.strict:
                        buf.append(text[i:])
                        break
                    raise ValueError("unmatched '{'")
                inner = text[i + 1 : end].strip()
                handled = False

                # ─ Wait ──────────────────────────────────────────────
                if inner == "":
                    out.append(TextToken("{}"))
                    handled = True
                elif m := self._RE_WAIT.fullmatch(inner):
                    out.append(WaitToken(float(m.group(1))))
                    handled = True
                # ─ Mouse ─────────────────────────────────────────────
                elif m := re.fullmatch(r"MOUSE_MOVE_(\d+)_(\d+)", inner):
                    out.append(MouseMoveToken(int(m.group(1)),
                                              int(m.group(2))))
                    handled = True
                elif m := re.fullmatch(r"MOUSE_CLICK_(\w+)", inner):
                    out.append(MouseClickToken(btn=m.group(1).lower()))
                    handled = True
                # ─ Key combo ─────────────────────────────────────────
                else:
                    parts = [p.strip() for p in re.split(r"\s*\+\s*", inner)]
                    keys: list[str] = []
                    valid = True
                    for p in parts:
                        if not p:
                            valid = False
                            break
                        if m := self._RE_SPEC.fullmatch(p):  # named <shift>
                            keys.append(m.group(1).lower())
                        elif len(p) == 1:                     # literal "a"
                            keys.append(p)
                        else:
                            valid = False
                            break
                    if valid and keys:
                        out.append(KeyToken(keys))
                        handled = True

                if not handled:
                    logger.warning("Skipping invalid sequence {%s}", inner)
                i = end + 1
                continue

            # Plain text
            buf.append(text[i])
            i += 1

        flush()

        # Merge adjacent TextTokens
        merged: list[Token] = []
        for t in out:
            if (
                merged
                and isinstance(t, TextToken)
                and isinstance(merged[-1], TextToken)
            ):
                merged[-1].text += t.text
            else:
                merged.append(t)
        return merged


# ─────────────────────────── Executor ──────────────────────────────
class Typist:
    def __init__(
        self,
        config: TypistConfig,
        backend=None,
        strict: bool = False,
    ):
        self.config  = config
        self.strict  = strict

        # ---- OS input back-end (pyautogui by default) -----------------
        if backend is None:
            if "DISPLAY" not in os.environ and os.name != "nt":
                raise RuntimeError("No DISPLAY; use Xvfb or pass backend")
            import pyautogui as pg
            backend = pg
        self.backend = backend

        # ---- pynput (fallback for single chars) ----------------------
        try:
            from pynput.keyboard import Controller as PynController
            self.pynput = PynController()
            logger.info("Using pynput for fine-grained key events")
        except Exception:
            self.pynput = None

    # ---- Run a parsed script ----------------------------------------
    def execute(self, tokens: Iterable[Token]) -> None:
        for t in tokens:
            try:
                t.execute(self)
            except Exception as e:
                logger.error("Token exec error: %s", e)


# ───────────────────────────── Facade ──────────────────────────────
class TextTyper:
    """High-level convenience wrapper."""
    def __init__(
        self,
        text: str,
        config: TypistConfig | None = None,
        backend=None,
        strict: bool = False,
    ):
        self.text    = text
        self.config  = config or TypistConfig()
        self.backend = backend
        self.strict  = strict

        self._parser = CommandParser(strict=strict)
        self._typist = Typist(self.config, backend=self.backend, strict=strict)
        if self.backend is None:
            self.backend = self._typist.backend  # use what Typist picked

    def simulate_typing(self) -> None:
        tokens = self._parser.parse(self.text)
        logger.info("Parsed %d tokens", len(tokens))
        self._typist.execute(tokens)
