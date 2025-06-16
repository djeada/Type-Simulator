import re
import time
import logging
import random
import os
import shutil
import subprocess
from abc import ABC, abstractmethod

# Configure logging
tlogging = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Clipboard Strategy Pattern
class ClipboardStrategy(ABC):
    @abstractmethod
    def copy(self, text: str): pass
    @abstractmethod
    def paste(self) -> str: pass

class PyperclipClipboard(ClipboardStrategy):
    def __init__(self):
        import pyperclip
        self._clip = pyperclip
        try:
            self._clip.copy("")
            _ = self._clip.paste()
        except Exception as e:
            raise RuntimeError(f"Pyperclip unavailable: {e}")

    def copy(self, text: str): self._clip.copy(text)
    def paste(self) -> str: return self._clip.paste()

class PlatformClipboard(ClipboardStrategy):
    def __init__(self):
        self.commands = self._detect_commands()
        if not self.commands:
            raise RuntimeError("No platform clipboard commands found")

    def _detect_commands(self):
        cmds = {}
        if shutil.which("pbcopy") and shutil.which("pbpaste"):
            cmds['copy'] = ['pbcopy']; cmds['paste'] = ['pbpaste']
        elif shutil.which("xclip"):
            cmds['copy'] = ['xclip', '-selection', 'clipboard']; cmds['paste'] = ['xclip', '-selection', 'clipboard', '-o']
        elif shutil.which("xsel"):
            cmds['copy'] = ['xsel', '--clipboard', '--input']; cmds['paste'] = ['xsel', '--clipboard', '--output']
        elif os.name == 'nt' and shutil.which('clip'):
            cmds['copy'] = ['clip']
        return cmds

    def copy(self, text: str):
        if 'copy' in self.commands:
            proc = subprocess.Popen(self.commands['copy'], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode())
        else:
            raise RuntimeError("Platform copy command not available")

    def paste(self) -> str:
        if 'paste' in self.commands:
            return subprocess.check_output(self.commands['paste']).decode()
        raise RuntimeError("Platform paste command not available")

# Token definitions
class Token(ABC):
    @abstractmethod
    def execute(self, executor: 'Typist'): pass

class TextToken(Token):
    PROBLEMATIC = set(":<>?|@#")
    def __init__(self, text: str): self.text = text
    def execute(self, executor: 'Typist'):
        for ch in self.text:
            interval = max(0, executor.typing_speed + executor.typing_variance * (2*random.random()-1))
            try:
                if ch in self.PROBLEMATIC:
                    # First try direct unicode injection with pynput
                    if executor.pynput:
                        try:
                            executor.pynput.type(ch)
                            time.sleep(0.02)
                            continue
                        except Exception:
                            logger.warning(f"Pynput typing failed for '{ch}', falling back")
                    # Next clipboard fallback
                    if executor.clipboard:
                        executor.clipboard.copy(ch)
                        executor.backend.hotkey("ctrl", "v")
                        time.sleep(0.05)
                        continue
                # Default typing
                executor.backend.write(ch, interval=interval)
            except Exception as e:
                logger.error(f"Typing '{ch}' failed: {e}")

class WaitToken(Token):
    def __init__(self, duration: float): self.duration = duration
    def execute(self, executor: 'Typist'): time.sleep(self.duration)

class KeyToken(Token):
    def __init__(self, keys: list[str]): self.keys = keys
    def execute(self, executor: 'Typist'):
        try: executor.backend.hotkey(*self.keys)
        except Exception as e: logger.error(f"Hotkey {self.keys} failed: {e}")

class MouseMoveToken(Token):
    def __init__(self, x: int, y: int, duration: float = 0): self.x, self.y, self.duration = x, y, duration
    def execute(self, executor: 'Typist'):
        try: executor.backend.moveTo(self.x, self.y, duration=self.duration)
        except Exception as e: logger.error(f"MoveTo ({self.x},{self.y}) failed: {e}")

class MouseClickToken(Token):
    def __init__(self, button: str = "left", clicks: int = 1, interval: float = 0):
        self.button, self.clicks, self.interval = button, clicks, interval
    def execute(self, executor: 'Typist'):
        try: executor.backend.click(button=self.button, clicks=self.clicks, interval=self.interval)
        except Exception as e: logger.error(f"Click {self.button} failed: {e}")

# Parser with mode
class CommandParser:
    _SPECIAL_KEY_REGEX = re.compile(r"<([^>]+)>")
    _WAIT_REGEX = re.compile(r"^WAIT_(\d+(?:\.\d+)?)$")

    def __init__(self, strict: bool = False):
        self.strict = strict

    def parse(self, text: str) -> list[Token]:
        tokens, buf, i = [], [], 0
        def flush():
            if buf: tokens.append(TextToken("".join(buf))); buf.clear()
        while i < len(text):
            if text[i] == '\\' and i+1 < len(text):
                if text[i+1] == '{':
                    buf.append('{'); i+=2; continue
                elif text[i+1] == '}':
                    buf.append('}'); i+=2; continue
                else:
                    buf.append(text[i+1]); i+=2; continue
            if text[i] == '{':
                flush(); end = text.find('}', i)
                if end < 0:
                    msg = text[i:]
                    logger.warning(f"Unmatched '{{': '{msg}'")
                    if not self.strict: buf.append(msg)
                    break
                content = text[i+1:end]
                stripped = content.strip()
                handled = False
                # Allow whitespace around + and key names
                key_combo_pattern = r"\s*\+\s*"
                if m:=self._WAIT_REGEX.fullmatch(stripped):
                    tokens.append(WaitToken(float(m.group(1))))
                    handled=True
                elif m:=re.fullmatch(r"MOUSE_MOVE_(\d+)_(\d+)", stripped):
                    tokens.append(MouseMoveToken(int(m.group(1)), int(m.group(2))))
                    handled=True
                elif m:=re.fullmatch(r"MOUSE_CLICK_(\w+)", stripped):
                    tokens.append(MouseClickToken(button=m.group(1).lower()))
                    handled=True
                else:
                    # Split on +, allowing whitespace
                    parts = [p.strip() for p in re.split(key_combo_pattern, stripped)]
                    keys, valid = [], True
                    for p in parts:
                        if not p:
                            valid=False
                            break
                        if (m:=self._SPECIAL_KEY_REGEX.fullmatch(p)):
                            keys.append(m.group(1).lower())
                        elif len(p)==1:
                            keys.append(p)
                        else:
                            valid=False
                            break
                    if valid and keys:
                        tokens.append(KeyToken(keys))
                        handled=True
                if not handled:
                    logger.warning(f"Skipping invalid sequence: '{{{content}}}'")
                    # Do not append invalid sequence to buffer (skip it)
                i = end+1
            else:
                buf.append(text[i]); i+=1
        flush()
        # merge TextTokens
        merged=[]
        for t in tokens:
            if merged and isinstance(t, TextToken) and isinstance(merged[-1], TextToken): merged[-1].text+=t.text
            else: merged.append(t)
        return merged

# Typist
class Typist:
    def __init__(self, typing_speed: float=0.05, typing_variance: float=0.02, backend=None, strict: bool=False):
        self.typing_speed, self.typing_variance = typing_speed, typing_variance
        # backend selection
        if backend is None:
            if "DISPLAY" not in os.environ and os.name!='nt': raise RuntimeError("Missing DISPLAY; use Xvfb or custom backend.")
            import pyautogui; self.backend = pyautogui
        else: self.backend = backend
        # clipboard strategy
        clipboard = None
        try:
            clipboard = PyperclipClipboard(); logger.info("Using Pyperclip clipboard strategy")
        except Exception:
            try:
                clipboard = PlatformClipboard(); logger.info("Using Platform clipboard strategy")
            except Exception as e:
                logger.warning(f"No clipboard mechanism: {e}. Typing fallback only.")
        self.clipboard = clipboard
        # unicode typing support via pynput
        try:
            from pynput.keyboard import Controller as PController
            self.pynput = PController()
            logger.info("Using pynput for direct unicode typing")
        except Exception:
            self.pynput = None
        self.strict = strict

    def execute(self, tokens: list[Token]):
        for token in tokens:
            try: token.execute(self)
            except Exception as e: logger.error(f"Token error: {e}")

# Backward-compatible interface
class TextTyper:
    def __init__(self, text: str, typing_speed: float=0.05, typing_variance: float=0.05, backend=None, strict: bool=False):
        self.text, self.typing_speed, self.typing_variance, self.backend, self.strict = text, typing_speed, typing_variance, backend, strict
        self._parser = CommandParser(strict)
        self._typist = Typist(typing_speed, typing_variance, backend, strict)

    def simulate_typing(self):
        tokens = self._parser.parse(self.text)
        logger.info(f"Parsed {len(tokens)} tokens: {[type(t).__name__ for t in tokens]}")
        self._typist.execute(tokens)

# Usage:
# TextTyper("Symbols #<>?", strict=False).simulate_typing()
