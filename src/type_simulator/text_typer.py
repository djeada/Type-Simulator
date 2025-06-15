import re
import time
import logging
import random
import os
import shutil
import subprocess
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Clipboard Strategy Pattern
class ClipboardStrategy(ABC):
    @abstractmethod
    def copy(self, text: str):
        pass

    @abstractmethod
    def paste(self) -> str:
        pass

class PyperclipClipboard(ClipboardStrategy):
    def __init__(self):
        import pyperclip
        self._clip = pyperclip
        # Verify mechanism
        try:
            self._clip.copy("")
            _ = self._clip.paste()
        except Exception as e:
            raise RuntimeError(f"Pyperclip unavailable: {e}")

    def copy(self, text: str):
        self._clip.copy(text)

    def paste(self) -> str:
        return self._clip.paste()

class PlatformClipboard(ClipboardStrategy):
    def __init__(self):
        self.os_name = os.name
        self.commands = self._detect_commands()
        # Validate commands
        if not self.commands:
            raise RuntimeError("No platform clipboard commands found")

    def _detect_commands(self):
        cmds = {}
        # macOS
        if shutil.which("pbcopy") and shutil.which("pbpaste"):
            cmds['copy'] = ['pbcopy']
            cmds['paste'] = ['pbpaste']
        # Linux
        elif shutil.which("xclip"):
            cmds['copy'] = ['xclip', '-selection', 'clipboard']
            cmds['paste'] = ['xclip', '-selection', 'clipboard', '-o']
        elif shutil.which("xsel"):
            cmds['copy'] = ['xsel', '--clipboard', '--input']
            cmds['paste'] = ['xsel', '--clipboard', '--output']
        # Windows
        elif os.name == 'nt' and shutil.which('clip'):
            cmds['copy'] = ['clip']
            # No direct paste command; rely on Ctrl+V
        return cmds

    def copy(self, text: str):
        if 'copy' in self.commands:
            proc = subprocess.Popen(
                self.commands['copy'], stdin=subprocess.PIPE, stderr=subprocess.PIPE
            )
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
    def execute(self, executor: 'Typist'):
        pass

class TextToken(Token):
    PROBLEMATIC = set(":<>?|@#")

    def __init__(self, text: str):
        self.text = text

    def execute(self, executor: 'Typist'):
        for ch in self.text:
            interval = max(0, executor.typing_speed + (
                executor.typing_variance * (2 * random.random() - 1)
            ))
            try:
                if ch in self.PROBLEMATIC and executor.clipboard:
                    executor.clipboard.copy(ch)
                    executor.backend.hotkey("ctrl", "v")
                    time.sleep(0.05)
                else:
                    executor.backend.write(ch, interval=interval)
            except Exception as e:
                logger.error(f"Typing '{ch}' failed: {e}")

class WaitToken(Token):
    def __init__(self, duration: float):
        self.duration = duration

    def execute(self, executor: 'Typist'):
        time.sleep(self.duration)

class KeyToken(Token):
    def __init__(self, keys: list[str]):
        self.keys = keys

    def execute(self, executor: 'Typist'):
        try:
            executor.backend.hotkey(*self.keys)
        except Exception as e:
            logger.error(f"Hotkey {self.keys} failed: {e}")

class MouseMoveToken(Token):
    def __init__(self, x: int, y: int, duration: float = 0):
        self.x = x; self.y = y; self.duration = duration

    def execute(self, executor: 'Typist'):
        try:
            executor.backend.moveTo(self.x, self.y, duration=self.duration)
        except Exception as e:
            logger.error(f"MoveTo ({self.x},{self.y}) failed: {e}")

class MouseClickToken(Token):
    def __init__(self, button: str = "left", clicks: int = 1, interval: float = 0):
        self.button = button; self.clicks = clicks; self.interval = interval

    def execute(self, executor: 'Typist'):
        try:
            executor.backend.click(
                button=self.button, clicks=self.clicks, interval=self.interval
            )
        except Exception as e:
            logger.error(f"Click {self.button} failed: {e}")

# Parser
class CommandParser:
    _SPECIAL_KEY_REGEX = re.compile(r"<([^>]+)>")
    _WAIT_REGEX = re.compile(r"^WAIT_(\d+(?:\.\d+)?)$")

    def parse(self, text: str) -> list[Token]:
        tokens, buf, i = [], [], 0
        def flush():
            if buf: tokens.append(TextToken("".join(buf))); buf.clear()
        while i < len(text):
            if text[i] == '\\' and i+1 < len(text) and text[i+1] in '{}\\':
                buf.append(text[i+1]); i+=2; continue
            if text[i] == '{':
                flush()
                end = text.find('}', i)
                if end < 0:
                    logger.warning(f"Unmatched '{{' at {i}"); i+=1; continue
                content = text[i+1:end].strip()
                if m:= self._WAIT_REGEX.match(content): tokens.append(WaitToken(float(m.group(1))))
                elif m:=re.fullmatch(r"MOUSE_MOVE_(\d+)_(\d+)", content): tokens.append(MouseMoveToken(int(m.group(1)), int(m.group(2))))
                elif m:=re.fullmatch(r"MOUSE_CLICK_(\w+)", content): tokens.append(MouseClickToken(button=m.group(1).lower()))
                else:
                    parts, keys, valid = content.split('+'), [], True
                    for p in parts:
                        if not p: valid=False; break
                        if m:=self._SPECIAL_KEY_REGEX.fullmatch(p): keys.append(m.group(1).lower())
                        elif len(p)==1: keys.append(p)
                        else: logger.warning(f"Invalid key '{p}' in '{{{content}}}'"); valid=False; break
                    if valid and keys: tokens.append(KeyToken(keys))
                    else: logger.warning(f"Skipping invalid '{{{content}}}'")
                i=end+1
            else:
                buf.append(text[i]); i+=1
        flush()
        merged=[]
        for t in tokens:
            if merged and isinstance(t, TextToken) and isinstance(merged[-1], TextToken): merged[-1].text+=t.text
            else: merged.append(t)
        return merged

# Typist
class Typist:
    def __init__(self, typing_speed: float=0.05, typing_variance: float=0.02, backend=None):
        self.typing_speed, self.typing_variance = typing_speed, typing_variance
        # Backend setup
        if backend is None:
            if "DISPLAY" not in os.environ and os.name!='nt': raise RuntimeError("Missing DISPLAY; use Xvfb or custom backend.")
            import pyautogui; self.backend=pyautogui
        else: self.backend=backend
        # Clipboard strategy detection
        clipboard = None
        try:
            candidate = PyperclipClipboard()
            clipboard = candidate
            logger.info("Using Pyperclip clipboard strategy")
        except Exception:
            logger.info("Pyperclip not available; trying platform clipboard")
            try:
                candidate = PlatformClipboard()
                clipboard = candidate
                logger.info("Using Platform clipboard strategy")
            except Exception as e:
                logger.warning(f"No clipboard mechanism: {e}. Typing fallback only.")
        self.clipboard = clipboard

    def execute(self, tokens: list[Token]):
        for token in tokens:
            try: token.execute(self)
            except Exception as e: logger.error(f"Token error: {e}")

# Backward-compatible interface
class TextTyper:
    def __init__(self, text: str, typing_speed: float=0.05, typing_variance: float=0.05, backend=None):
        self.text, self.typing_speed, self.typing_variance, self.backend = text, typing_speed, typing_variance, backend
        self._parser = CommandParser()
        self._typist = Typist(typing_speed, typing_variance, backend)
    def simulate_typing(self):
        tokens = self._parser.parse(self.text)
        logger.info(f"Parsed {len(tokens)} tokens: {[type(t).__name__ for t in tokens]}")
        self._typist.execute(tokens)

# Example:
# TextTyper("Data #<ctrl>+s").simulate_typing()
