"""
robust_typist.py  –  keyboard-layout–proof virtual typist
"""

import os
import re
import sys
import time
import random
import shutil
import logging
import subprocess
from abc import ABC, abstractmethod

# ─────────────────────────── Logging ───────────────────────────
logging.basicConfig(
    level=logging.INFO,                      # flip to DEBUG for per-char trace
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────── Clipboard Strategies ───────────────────────
class ClipboardStrategy(ABC):
    @abstractmethod
    def copy(self, text: str) -> None: ...
    @abstractmethod
    def paste(self) -> str: ...

class PyperclipClipboard(ClipboardStrategy):
    def __init__(self):
        import pyperclip as pc
        self._clip = pc
        self._clip.copy("")
        _ = self._clip.paste()
    def copy(self, text: str): self._clip.copy(text)
    def paste(self) -> str:   return self._clip.paste()

class PlatformClipboard(ClipboardStrategy):
    def __init__(self):
        self.cmds = self._detect()
        if not self.cmds:
            raise RuntimeError("No platform clipboard commands")
    @staticmethod
    def _detect():
        c = {}
        if shutil.which("pbcopy") and shutil.which("pbpaste"):
            c["copy"], c["paste"] = ["pbcopy"], ["pbpaste"]
        elif shutil.which("xclip"):
            c["copy"] = ["xclip", "-selection", "clipboard"]
            c["paste"] = ["xclip", "-selection", "clipboard", "-o"]
        elif shutil.which("xsel"):
            c["copy"] = ["xsel", "--clipboard", "--input"]
            c["paste"] = ["xsel", "--clipboard", "--output"]
        elif os.name == "nt" and shutil.which("clip"):
            c["copy"] = ["clip"]                # no fast native paste on Win
        return c
    def copy(self, text: str):
        if "copy" not in self.cmds:
            raise RuntimeError("No copy cmd")
        proc = subprocess.Popen(self.cmds["copy"], stdin=subprocess.PIPE)
        proc.communicate(input=text.encode())
    def paste(self) -> str:
        if "paste" not in self.cmds:
            raise RuntimeError("No paste cmd")
        return subprocess.check_output(self.cmds["paste"]).decode()

class TkClipboard(ClipboardStrategy):
    def __init__(self):
        import tkinter as tk
        self._tk = tk.Tk(); self._tk.withdraw()
        self.copy(""); _ = self.paste()
    def copy(self, text: str):
        self._tk.clipboard_clear()
        self._tk.clipboard_append(text)
        self._tk.update()
    def paste(self) -> str:
        self._tk.update(); return self._tk.clipboard_get()

# ─────────────────────────── Token types ───────────────────────────
class Token(ABC):
    @abstractmethod
    def execute(self, executor: "Typist") -> None: ...

class TextToken(Token):
    PROBLEMATIC = set(":<>?|@#{}")

    # ordered by preference
    PASTE_CANDIDATES = (
        ("primary",   ("shift", "insert")),        # X11 & Linux terminals
       # ("clipboard", ("ctrl", "v")),              # Win / X11 / many apps
       # ("clipboard", ("command", "v")),           # macOS
    )
    PASTE_SETTLE = 0.12       # seconds to wait after a hot-key

    def __init__(self, text: str):
        self.text = text

    # ---------------- internal helpers ----------------
    @staticmethod
    def _copy_to_primary_x11(text: str) -> bool:
        """
        Low-level helper: copy to PRIMARY using xclip/xsel if present.
        Returns True on success.
        """
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
        """
        Layout-agnostic Unicode hex input: Ctrl+Shift+U, hex, Space
        Works in virtually every Gtk/Qt/terminal program.
        """
        hexcode = format(ord(ch), "x")
        backend.hotkey("ctrl", "shift", "u")
        time.sleep(0.05)
        backend.write(hexcode)
        backend.press("space")
        time.sleep(0.05)

    # ---------------- main execute ----------------
    def execute(self, executor: "Typist"):
        for ch in self.text:
            interval = max(
                0,
                executor.typing_speed
                + executor.typing_variance * (2 * random.random() - 1),
            )

            if ch in self.PROBLEMATIC:
                # Try every paste candidate in order
                for target, hotkey in self.PASTE_CANDIDATES:
                    if target == "clipboard" and executor.clipboard:
                        prev = executor.clipboard.paste()
                        executor.clipboard.copy(ch)
                        logger.debug("Typing %r via %s (%s)",
                                     ch, target, "+".join(hotkey))
                        try:
                            executor.backend.hotkey(*hotkey)
                            time.sleep(self.PASTE_SETTLE)
                            executor.clipboard.copy(prev)
                            break                       # success
                        except Exception as e:
                            logger.debug("Hot-key failed: %s", e)
                            executor.clipboard.copy(prev)
                    elif target == "primary":
                        if self._copy_to_primary_x11(ch):
                            logger.debug("Typing %r via PRIMARY (+Shift-Insert)",
                                         ch)
                            try:
                                executor.backend.hotkey(*hotkey)
                                time.sleep(self.PASTE_SETTLE)
                                break                   # success
                            except Exception as e:
                                logger.debug("Shift-Insert failed: %s", e)
                else:
                    # No clipboard route worked – fall back
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
                    continue
                # paste path succeeded – next character
                continue

            # ordinary characters
            logger.debug("Typing %r via write()", ch)
            executor.backend.write(ch, interval=interval)


class WaitToken(Token):
    def __init__(self, seconds: float): self.seconds = seconds
    def execute(self, executor): time.sleep(self.seconds)

class KeyToken(Token):
    def __init__(self, keys: list[str]): self.keys = keys
    def execute(self, executor):
        logger.debug("Hotkey %s", "+".join(self.keys))
        executor.backend.hotkey(*self.keys)

class MouseMoveToken(Token):
    def __init__(self, x: int, y: int, dur: float = 0):
        self.x,self.y,self.dur = x,y,dur
    def execute(self, executor):
        logger.debug("Mouse move to (%d,%d)", self.x,self.y)
        executor.backend.moveTo(self.x, self.y, duration=self.dur)

class MouseClickToken(Token):
    def __init__(self, btn="left", clicks=1, interval=0):
        self.btn,self.clicks,self.interval = btn,clicks,interval
    def execute(self, executor):
        logger.debug("Mouse click %s ×%d", self.btn, self.clicks)
        executor.backend.click(button=self.btn, clicks=self.clicks,
                               interval=self.interval)

# ─────────────────────────── Parser ───────────────────────────
class CommandParser:
    _RE_WAIT = re.compile(r"^WAIT_(\d+(?:\.\d+)?)$")
    _RE_SPEC = re.compile(r"<([^>]+)>")
    def __init__(self, strict=False): self.strict = strict

    def parse(self, text: str) -> list[Token]:
        out, buf, i = [], [], 0
        def flush():
            if buf: out.append(TextToken("".join(buf))); buf.clear()
        while i < len(text):
            if text[i] == "\\" and i+1 < len(text) and text[i+1] in "{}\\":
                buf.append(text[i+1]); i += 2; continue
            if text[i] == "{":
                flush(); end = text.find("}", i)
                if end < 0:
                    if not self.strict: buf.append(text[i:]); break
                    raise ValueError("unmatched '{'")
                inner = text[i+1:end].strip()
                handled = False
                if inner == "":                              # literal {}
                    out.append(TextToken("{}")); handled=True
                elif m:=self._RE_WAIT.fullmatch(inner):
                    out.append(WaitToken(float(m.group(1)))); handled=True
                elif m:=re.fullmatch(r"MOUSE_MOVE_(\d+)_(\d+)", inner):
                    out.append(MouseMoveToken(int(m.group(1)), int(m.group(2))))
                    handled=True
                elif m:=re.fullmatch(r"MOUSE_CLICK_(\w+)", inner):
                    out.append(MouseClickToken(btn=m.group(1).lower()))
                    handled=True
                else:                                       # key combo
                    parts=[p.strip() for p in re.split(r"\s*\+\s*", inner)]
                    keys, valid = [], True
                    for p in parts:
                        if not p: valid=False; break
                        if m:=self._RE_SPEC.fullmatch(p): keys.append(m.group(1).lower())
                        elif len(p)==1: keys.append(p)
                        else: valid=False; break
                    if valid and keys:
                        out.append(KeyToken(keys)); handled=True
                if not handled:
                    logger.warning("Skipping invalid sequence {%s}", inner)
                i = end+1; continue
            buf.append(text[i]); i+=1
        flush()
        # merge neighbour TextTokens
        merged=[]
        for t in out:
            if merged and isinstance(t, TextToken) and isinstance(merged[-1], TextToken):
                merged[-1].text += t.text
            else: merged.append(t)
        return merged

# ─────────────────────────── Typist ───────────────────────────
class Typist:
    def __init__(self, typing_speed=.05, typing_variance=.02,
                 backend=None, strict=False):
        self.typing_speed, self.typing_variance = typing_speed, typing_variance
        if backend is None:
            if "DISPLAY" not in os.environ and os.name!="nt":
                raise RuntimeError("No DISPLAY; use Xvfb or supply backend")
            import pyautogui as pg; backend = pg
        self.backend = backend
        # clipboard: try pyperclip, platform, tk
        self.clipboard = None
        for strat in (PyperclipClipboard, PlatformClipboard, TkClipboard):
            try:
                self.clipboard = strat()
                logger.info("Using %s clipboard", strat.__name__); break
            except Exception as e:
                logger.debug("%s unavailable: %s", strat.__name__, e)
        try:
            from pynput.keyboard import Controller as PC
            self.pynput = PC(); logger.info("Using pynput")
        except Exception:
            self.pynput = None
        self.strict = strict

    def execute(self, toks: list[Token]):
        for t in toks:
            try: t.execute(self)
            except Exception as e: logger.error("Token exec error: %s", e)

# ─────────────────────────── Facade ───────────────────────────
class TextTyper:
    def __init__(self, text: str, typing_speed=.05, typing_variance=.05,
                 backend=None, strict=False):
        self.text=text; self.typing_speed=typing_speed
        self.typing_variance=typing_variance; self.backend=backend
        self.strict=strict
        self._parser = CommandParser(strict)
        self._typist = Typist(typing_speed, typing_variance,
                              backend, strict)
        if self.backend is None: self.backend = self._typist.backend

    def simulate_typing(self):
        toks = self._parser.parse(self.text)
        logger.info("Parsed %d tokens", len(toks))
        self._typist.execute(toks)

# ─────────────────────────── Self-test ───────────────────────────
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    TextTyper(r"<>:{}|@#  {WAIT_0.2}  Hello!".strip()).simulate_typing()
