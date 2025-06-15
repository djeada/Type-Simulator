import re
import time
import logging
import random
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Token:
    def execute(self, executor):
        raise NotImplementedError


class TextToken(Token):
    def __init__(self, text: str):
        self.text = text

    def execute(self, executor):
        # Only use clipboard-paste for problematic characters
        PROBLEMATIC = {":", "<", ">", "?", "|", "@", "#"}
        try:
            import pyperclip
            import pyautogui
        except ImportError:
            pyperclip = None
            pyautogui = None
        for ch in self.text:
            interval = executor.typing_speed + (
                executor.typing_variance * (2 * random.random() - 1)
            )
            if ch in PROBLEMATIC and pyperclip and pyautogui:
                pyperclip.copy(ch)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
            else:
                executor.backend.write(ch, interval=interval)


class WaitToken(Token):
    def __init__(self, duration: float):
        self.duration = duration

    def execute(self, executor):
        time.sleep(self.duration)


class KeyToken(Token):
    def __init__(self, keys: list[str]):
        self.keys = keys

    def execute(self, executor):
        executor.backend.hotkey(*self.keys)


class MouseMoveToken(Token):
    def __init__(self, x: int, y: int, duration: float = 0):
        self.x = x
        self.y = y
        self.duration = duration

    def execute(self, executor):
        executor.backend.moveTo(self.x, self.y, duration=self.duration)


class MouseClickToken(Token):
    def __init__(self, button: str = "left", clicks: int = 1, interval: float = 0):
        self.button = button
        self.clicks = clicks
        self.interval = interval

    def execute(self, executor):
        executor.backend.click(
            button=self.button, clicks=self.clicks, interval=self.interval
        )


class CommandParser:
    """
    Parses input text into tokens (TextToken, WaitToken, KeyToken, MouseMoveToken, MouseClickToken).
    - Escaped braces: '\{' and '\}' produce literal '{' and '}'.
    - {WAIT_x} pauses x seconds.
    - {MOUSE_MOVE_x_y} moves the cursor to (x, y).
    - {MOUSE_CLICK_button} clicks the mouse (button: left/right/middle).
    - {<key>+...} presses keys simultaneously.

    Invalid sequences are skipped with a warning.
    """

    _SPECIAL_KEY_REGEX = re.compile(r"<([^>]+)>")
    _WAIT_REGEX = re.compile(r"^WAIT_(\d+(?:\.\d+)?)$")

    def parse(self, text: str) -> list[Token]:
        tokens: list[Token] = []
        buffer: list[str] = []
        i = 0

        def flush_buffer():
            if buffer:
                tokens.append(TextToken("".join(buffer)))
                buffer.clear()

        while i < len(text):
            # Drop redundant backslash before escape
            if text[i] == "\\" and i + 1 < len(text) and text[i + 1] == "\\":
                i += 1
                continue
            ch = text[i]
            # Escaped brace
            if ch == "\\" and i + 1 < len(text) and text[i + 1] in "{}":
                buffer.append(text[i + 1])
                i += 2
                continue

            if ch == "{":
                flush_buffer()
                end = text.find("}", i)
                if end == -1:
                    logger.warning(f"Unmatched '{{' at position {i}")
                    i += 1
                    continue
                content = text[i + 1 : end]
                cleaned = "".join(content.split())
                # WAIT
                m_wait = self._WAIT_REGEX.match(cleaned)
                if m_wait:
                    tokens.append(WaitToken(float(m_wait.group(1))))
                else:
                    # MOUSE_MOVE
                    m_move = re.match(r"^MOUSE_MOVE_(\d+)_(\d+)$", cleaned)
                    if m_move:
                        x, y = int(m_move.group(1)), int(m_move.group(2))
                        tokens.append(MouseMoveToken(x, y))
                    else:
                        # MOUSE_CLICK
                        m_click = re.match(r"^MOUSE_CLICK_(\w+)$", cleaned)
                        if m_click:
                            btn = m_click.group(1).lower()
                            tokens.append(MouseClickToken(button=btn))
                        else:
                            # Key sequence
                            parts = cleaned.split("+")
                            keys = []
                            valid = True
                            for part in parts:
                                if not part:
                                    valid = False
                                    break
                                m_key = self._SPECIAL_KEY_REGEX.fullmatch(part)
                                if m_key:
                                    keys.append(m_key.group(1).lower())
                                elif len(part) == 1:
                                    keys.append(part)
                                else:
                                    logger.warning(
                                        f"Invalid key '{part}' in '{{{content}}}'"
                                    )
                                    valid = False
                                    break
                            if valid and keys:
                                tokens.append(KeyToken(keys))
                            else:
                                logger.warning(
                                    f"Skipping invalid sequence '{{{content}}}'"
                                )
                i = end + 1
            else:
                buffer.append(ch)
                i += 1
        flush_buffer()
        # Merge adjacent TextTokens
        merged: list[Token] = []
        for t in tokens:
            if (
                merged
                and isinstance(t, TextToken)
                and isinstance(merged[-1], TextToken)
            ):
                merged[-1].text += t.text
            else:
                merged.append(t)
        return merged


class Typist:
    """
    Executes tokens via a backend (pyautogui by default).
    """

    def __init__(
        self, typing_speed: float = 0.05, typing_variance: float = 0.02, backend=None
    ):
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance
        if backend is None:
            if "DISPLAY" not in os.environ:
                raise RuntimeError(
                    "pyautogui requires a running X server. Please run your tests under Xvfb or set DISPLAY."
                )
            import pyautogui

            self.backend = pyautogui
        else:
            self.backend = backend

    def execute(self, tokens: list[Token]):
        for token in tokens:
            try:
                token.execute(self)
            except Exception as e:
                logging.error(f"Error executing {token}: {e}")


class TextTyper:
    """
    Backward-compatible interface:
    TextTyper(text, typing_speed, typing_variance)
    """

    def __init__(
        self,
        text: str,
        typing_speed: float = 0.05,
        typing_variance: float = 0.05,
        backend=None,
    ):
        self.text = text
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance
        self.backend = backend
        self._parser = CommandParser()
        self._typist = Typist(typing_speed, typing_variance, backend)

    def simulate_typing(self):
        tokens = self._parser.parse(self.text)
        logger.info(
            f"Parsed tokens: {[type(t).__name__ + ':' + (','.join(t.keys) if hasattr(t,'keys') else getattr(t,'text',str(t.duration) if hasattr(t,'duration') else getattr(t,'x',None) and getattr(t,'y',None) and f'{t.x},{t.y}' or '')) for t in tokens]}"
        )
        self._typist.execute(tokens)
