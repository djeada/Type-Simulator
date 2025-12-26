import re
import logging
from typing import List, Optional

from type_simulator.text_typer.token import (
    Token,
    TextToken,
    WaitToken,
    MouseMoveToken,
    MouseClickToken,
    KeyToken,
    RepeatToken,
    RandomTextToken,
    VariableToken,
    SpeedToken,
)

logger = logging.getLogger(__name__)


class CommandParser:
    """
    Parses command strings with embedded control sequences into a list of Tokens.
    Supports literal braces, waits, mouse moves/clicks, and key combos.

    If strict is False, invalid sequences remain as literal text tokens.
    If strict is True, unmatched or invalid specs raise or are skipped with a warning.
    """

    _RE_WAIT = re.compile(r"WAIT_(?P<secs>\d+(?:\.\d+)?)$")
    _RE_MOUSE_MOVE = re.compile(r"MOUSE_MOVE_(?P<x>\d+)_(?P<y>\d+)$")
    _RE_MOUSE_CLICK = re.compile(r"MOUSE_CLICK_(?P<btn>\w+)$")
    _RE_SPEC = re.compile(r"<(?P<key>[^>]+)>$")
    _RE_REPEAT_START = re.compile(r"REPEAT_(?P<count>\d+)$")
    _RE_REPEAT_END = re.compile(r"/REPEAT$")
    _RE_RANDOM = re.compile(
        r"RANDOM_(?P<length>\d+)(?:_(?P<charset>alphanumeric|alpha|numeric|custom:[^\}]+))?$"
    )
    _RE_VAR_SET = re.compile(r"SET_(?P<name>\w+)=(?P<value>.*)$")
    _RE_VAR_GET = re.compile(r"GET_(?P<name>\w+)$")
    _RE_SPEED = re.compile(
        r"SPEED_(?P<speed>\d+(?:\.\d+)?)(?:_(?P<variance>\d+(?:\.\d+)?))?$"
    )

    def __init__(self, strict: bool = False):
        self.strict = strict

    def parse(self, text: str) -> List[Token]:
        tokens: List[Token] = []
        buffer: List[str] = []
        idx, length = 0, len(text)
        repeat_stack: List[tuple] = []  # Stack of (count, start_tokens_idx)

        def flush_buffer() -> None:
            if buffer:
                tokens.append(TextToken("".join(buffer)))
                buffer.clear()

        while idx < length:
            ch = text[idx]
            # Escape for literal braces or backslash
            if ch == "\\" and idx + 1 < length and text[idx + 1] in "{}\\":
                buffer.append(text[idx + 1])
                idx += 2
                continue

            if ch == "{":
                flush_buffer()
                end_idx = text.find("}", idx)
                if end_idx < 0:
                    if not self.strict:
                        # treat unmatched as literal text
                        buffer.append(text[idx:])
                        break
                    raise ValueError("Unmatched '{' in input")

                spec = text[idx + 1 : end_idx]

                # Check for REPEAT_N start
                m = self._RE_REPEAT_START.fullmatch(spec.strip())
                if m:
                    repeat_stack.append((int(m.group("count")), len(tokens)))
                    idx = end_idx + 1
                    continue

                # Check for /REPEAT end
                if self._RE_REPEAT_END.fullmatch(spec.strip()):
                    if repeat_stack:
                        count, start_idx = repeat_stack.pop()
                        repeat_tokens = tokens[start_idx:]
                        tokens = tokens[:start_idx]
                        tokens.append(RepeatToken(count, repeat_tokens))
                    idx = end_idx + 1
                    continue

                token = self._parse_spec(spec)

                if token:
                    tokens.append(token)
                else:
                    # Escape control characters for clearer logging visibility
                    def _escape(s: str) -> str:
                        s = s.replace("\\", r"\\")
                        s = s.replace("\n", r"\n").replace("\r", r"\r")
                        return s
                    preview = _escape(spec)
                    if len(preview) > 200:
                        preview = preview[:200] + "…"
                    msg = f"Invalid sequence '{{{preview}}}'"
                    if self.strict:
                        logger.warning(msg)
                        # skip invalid spec in strict mode
                    else:
                        logger.debug("%s, treating as literal", msg)
                        # treat as literal text
                        tokens.append(TextToken(f"{{{spec}}}"))

                idx = end_idx + 1
                continue

            buffer.append(ch)
            idx += 1

        flush_buffer()
        return self._merge_text_tokens(tokens)

    def _parse_spec(self, spec: str) -> Optional[Token]:
        # Empty braces means literal {}
        if spec == "":
            return TextToken("{}")
        # Wait - strip whitespace for patterns that expect clean input
        m = self._RE_WAIT.fullmatch(spec.strip())
        if m:
            return WaitToken(float(m.group("secs")))
        # Mouse move
        m = self._RE_MOUSE_MOVE.fullmatch(spec.strip())
        if m:
            return MouseMoveToken(int(m.group("x")), int(m.group("y")))
        # Mouse click
        m = self._RE_MOUSE_CLICK.fullmatch(spec.strip())
        if m:
            return MouseClickToken(btn=m.group("btn").lower())
        # Random text generation
        m = self._RE_RANDOM.fullmatch(spec.strip())
        if m:
            length = int(m.group("length"))
            charset = m.group("charset") or "alphanumeric"
            return RandomTextToken(length=length, charset=charset)
        # Variable set
        m = self._RE_VAR_SET.fullmatch(spec.strip())
        if m:
            return VariableToken(
                name=m.group("name"), value=m.group("value"), action="set"
            )
        # Variable get
        m = self._RE_VAR_GET.fullmatch(spec.strip())
        if m:
            return VariableToken(name=m.group("name"), action="get")
        # Speed change
        m = self._RE_SPEED.fullmatch(spec.strip())
        if m:
            speed = float(m.group("speed"))
            variance = float(m.group("variance")) if m.group("variance") else None
            return SpeedToken(speed=speed, variance=variance)
        # Key combination - strip for patterns
        parts = [p.strip() for p in re.split(r"\s*\+\s*", spec.strip())]
        keys: List[str] = []
        for part in parts:
            if not part:
                return None
            m = self._RE_SPEC.fullmatch(part)
            if m:
                keys.append(m.group("key").lower())
            elif len(part) == 1:
                keys.append(part)
            else:
                return None
        return KeyToken(keys) if keys else None

    @staticmethod
    def _merge_text_tokens(tokens: List[Token]) -> List[Token]:
        merged: List[Token] = []
        for tok in tokens:
            if (
                merged
                and isinstance(tok, TextToken)
                and isinstance(merged[-1], TextToken)
            ):
                merged[-1].text += tok.text
            else:
                merged.append(tok)
        return merged
