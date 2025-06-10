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
        for ch in self.text:
            interval = executor.typing_speed + (
                executor.typing_variance * (2 * random.random() - 1)
            )
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


class CommandParser:
    """
    Parses input text into tokens (TextToken, WaitToken, KeyToken).
    - Escaped braces: '\{' and '\}' produce literal '{' and '}'.
    - {WAIT_x} pauses x seconds.
    - {<key>+...} presses keys simultaneously.

    Invalid sequences are skipped with a warning.
    """

    _SPECIAL_KEY_REGEX = re.compile(r"<([^>]+)>")
    _WAIT_REGEX = re.compile(r"^WAIT_(\d+(?:\.\d+)?)$")

    def parse(self, text: str) -> list[Token]:
        tokens = []
        buffer = []
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
                            logger.warning(f"Invalid key '{part}' in '{{{content}}}'")
                            valid = False
                            break
                    if valid and keys:
                        tokens.append(KeyToken(keys))
                    else:
                        logger.warning(f"Skipping invalid sequence '{{{content}}}'")
                i = end + 1
            else:
                buffer.append(ch)
                i += 1
        flush_buffer()
        # Merge adjacent TextTokens
        merged = []
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
            if 'DISPLAY' not in os.environ:
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
        # Debug: log parsed tokens
        tokens = self._parser.parse(self.text)
        logger.info(
            f"Parsed tokens: {[type(t).__name__ + ':' + (','.join(t.keys) if hasattr(t,'keys') else getattr(t,'text',str(t.duration) if hasattr(t,'duration') else '')) for t in tokens]}"
        )
        self._typist.execute(tokens)
        return
        tokens = self._parser.parse(self.text)
        self._typist.execute(tokens)
