import sys
import time
import random
import shutil
import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Configure logger
logger = logging.getLogger(__name__)

# Problematic characters requiring clipboard or unicode input
PROBLEMATIC_CHARS = set(str("<>:?|@#{}:;*[]()!$&'^,~`\\"))  # expanded set as needed

# Paste strategies ordered by preference
PASTE_STRATEGIES: List[Tuple[str, Tuple[str, ...]]] = [
    ("primary", ("shift", "insert")),  # X11 primary selection
    # ("clipboard", ("ctrl", "v")),   # standard clipboard
    # ("clipboard", ("command", "v")),# macOS clipboard
]


def _copy_to_primary_x11(text: str) -> bool:
    """
    Copy `text` to X11 PRIMARY selection using xclip or xsel.
    Returns True on success.
    """
    for tool, args in (
        ("xclip", ["xclip", "-selection", "primary"]),
        ("xsel", ["xsel", "--primary", "--input"]),
    ):
        if shutil.which(tool):
            try:
                proc = subprocess.Popen(args, stdin=subprocess.PIPE)
                proc.communicate(text.encode())
                if proc.returncode == 0:
                    return True
            except Exception:
                logger.debug("%s failed, trying next tool", tool, exc_info=True)
    return False


def _type_unicode_hex(ch: str, backend, typing_speed: float) -> None:
    """
    Input Unicode character via Ctrl+Shift+U hex input (Linux/Gtk/Qt).
    """
    hex_code = f"{ord(ch):x}"
    backend.hotkey("ctrl", "shift", "u")
    time.sleep(typing_speed)
    backend.write(hex_code)
    backend.press("space")
    time.sleep(typing_speed)


class Token(ABC):
    """Base class for all action tokens."""

    @abstractmethod
    def execute(self, executor: "Typist") -> None: ...


@dataclass
class TextToken(Token):
    text: str

    def execute(self, executor: "Typist") -> None:
        for ch in self.text:
            interval = max(
                0.0,
                executor.typing_speed
                + executor.typing_variance * (2 * random.random() - 1),
            )
            # Handle newline as Enter keypress
            if ch == '\n':
                logger.debug("Typing newline via Enter key")
                executor.backend.press('enter')
                time.sleep(interval)
            elif ch in PROBLEMATIC_CHARS:
                if self._paste_character(ch, executor):
                    continue
                self._fallback_type(ch, executor, interval)
            else:
                logger.debug("Typing '%s' via write", ch)
                executor.backend.write(ch, interval=interval)

    @staticmethod
    def _paste_character(ch: str, executor: "Typist") -> bool:
        # Attempt each paste strategy
        for target, keys in PASTE_STRATEGIES:
            try:
                if target == "primary" and _copy_to_primary_x11(ch):
                    logger.debug("Pasting '%s' via %s", ch, target)
                    executor.backend.hotkey(*keys)
                    time.sleep(executor.typing_speed)
                    return True
                elif target == "clipboard" and executor.clipboard:
                    prev = executor.clipboard.paste()
                    executor.clipboard.copy(ch)
                    logger.debug("Pasting '%s' via clipboard + %s", ch, "+".join(keys))
                    executor.backend.hotkey(*keys)
                    time.sleep(executor.typing_speed)
                    executor.clipboard.copy(prev)
                    return True
            except Exception as e:
                logger.debug("Paste via %s failed: %s", target, e, exc_info=True)
        return False

    @staticmethod
    def _fallback_type(ch: str, executor: "Typist", interval: float) -> None:
        # Fallback methods: unicode hex, pynput, or direct write
        if sys.platform.startswith("linux"):
            logger.debug("Typing '%s' via unicode hex input", ch)
            _type_unicode_hex(ch, executor.backend, executor.typing_speed)
        elif getattr(executor, "pynput", None):
            logger.debug("Typing '%s' via pynput", ch)
            executor.pynput.type(ch)
            time.sleep(executor.typing_speed)
        else:
            logger.debug("Typing '%s' via write", ch)
            executor.backend.write(ch, interval=interval)


@dataclass
class WaitToken(Token):
    seconds: float

    def execute(self, executor: "Typist") -> None:
        logger.debug("Waiting for %s seconds", self.seconds)
        time.sleep(self.seconds)


@dataclass
class KeyToken(Token):
    keys: List[str]

    def execute(self, executor: "Typist") -> None:
        logger.debug("Hotkey: %s", "+".join(self.keys))
        executor.backend.hotkey(*self.keys)


@dataclass
class MouseMoveToken(Token):
    x: int
    y: int
    duration: float = 0.0

    def execute(self, executor: "Typist") -> None:
        logger.debug(
            "Moving mouse to (%d, %d) over %0.2fs", self.x, self.y, self.duration
        )
        executor.backend.moveTo(self.x, self.y, duration=self.duration)


@dataclass
class MouseClickToken(Token):
    button: str = "left"
    clicks: int = 1
    interval: float = 0.0

    def execute(self, executor: "Typist") -> None:
        logger.debug("Clicking %s button %d time(s)", self.button, self.clicks)
        executor.backend.click(
            button=self.button, clicks=self.clicks, interval=self.interval
        )


@dataclass
class RepeatToken(Token):
    """Repeat a sequence of tokens N times."""

    count: int
    tokens: List[Token]

    def execute(self, executor: "Typist") -> None:
        logger.debug("Repeating %d tokens %d time(s)", len(self.tokens), self.count)
        for i in range(self.count):
            logger.debug("Repeat iteration %d/%d", i + 1, self.count)
            for token in self.tokens:
                token.execute(executor)


@dataclass
class RandomTextToken(Token):
    """Generate random text of specified length and character set."""

    length: int
    charset: str = "alphanumeric"  # alphanumeric, alpha, numeric, custom:abc123

    def execute(self, executor: "Typist") -> None:
        import string

        if self.charset == "alphanumeric":
            chars = string.ascii_letters + string.digits
        elif self.charset == "alpha":
            chars = string.ascii_letters
        elif self.charset == "numeric":
            chars = string.digits
        elif self.charset.startswith("custom:"):
            chars = self.charset[7:]
        else:
            chars = string.ascii_letters + string.digits

        text = "".join(random.choice(chars) for _ in range(self.length))
        logger.debug("Typing random text: %s", text)
        TextToken(text).execute(executor)


@dataclass
class VariableToken(Token):
    """Store or retrieve a variable value."""

    name: str
    value: Optional[str] = None
    action: str = "get"  # get, set

    def execute(self, executor: "Typist") -> None:
        if not hasattr(executor, "_variables"):
            executor._variables = {}

        if self.action == "set":
            executor._variables[self.name] = self.value
            logger.debug("Set variable %s = %s", self.name, self.value)
        else:  # get
            val = executor._variables.get(self.name, "")
            logger.debug("Get variable %s = %s", self.name, val)
            if val:
                TextToken(val).execute(executor)


@dataclass
class SpeedToken(Token):
    """Temporarily change typing speed for following tokens."""

    speed: float
    variance: Optional[float] = None

    def execute(self, executor: "Typist") -> None:
        logger.debug(
            "Changing typing speed to %0.3fs (variance: %s)",
            self.speed,
            self.variance,
        )
        executor.typing_speed = self.speed
        if self.variance is not None:
            executor.typing_variance = self.variance
