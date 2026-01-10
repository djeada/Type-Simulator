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
    DateTimeToken,
    CounterToken,
    LoopToken,
    NewlineToken,
    TabToken,
)

logger = logging.getLogger(__name__)


class CommandParser:
    """
    Parses command strings with embedded control sequences into a list of Tokens.

    Supports:
    - Literal braces (escape with backslash)
    - Wait/pause commands
    - Mouse moves and clicks
    - Key combinations and shortcuts
    - Repeat blocks
    - Random text generation
    - Variables (set/get)
    - Speed changes
    - Date/time insertion
    - Counters
    - Loops with iteration variables
    - Newlines and tabs

    If strict is False, invalid sequences remain as literal text tokens.
    If strict is True, unmatched or invalid specs raise or are skipped with a warning.
    """

    _RE_WAIT = re.compile(r"WAIT_(?P<secs>\d+(?:\.\d+)?)$")
    _RE_MOUSE_MOVE = re.compile(r"MOUSE_MOVE_(?P<x>\d+)_(?P<y>\d+)$")
    _RE_MOUSE_CLICK = re.compile(r"MOUSE_CLICK_(?P<btn>\w+)$")
    _RE_SPEC = re.compile(r"<(?P<key>[^>]+)>$")
    _RE_REPEAT_START = re.compile(r"REPEAT_(?P<count>\d+)$")
    _RE_REPEAT_END = re.compile(r"/REPEAT$")
    _RE_LOOP_START = re.compile(r"LOOP_(?P<count>\d+)(?:_(?P<var>\w+))?$")
    _RE_LOOP_END = re.compile(r"/LOOP$")
    _RE_RANDOM = re.compile(
        r"RANDOM_(?P<length>\d+)(?:_(?P<charset>alphanumeric|alpha|numeric|custom:[^\}]+))?$"
    )
    _RE_VAR_SET = re.compile(r"SET_(?P<name>\w+)=(?P<value>.*)$")
    _RE_VAR_GET = re.compile(r"GET_(?P<name>\w+)$")
    _RE_SPEED = re.compile(
        r"SPEED_(?P<speed>\d+(?:\.\d+)?)(?:_(?P<variance>\d+(?:\.\d+)?))?$"
    )
    _RE_DATETIME = re.compile(r"DATETIME(?:_(?P<format>.+))?$")
    _RE_DATE = re.compile(r"DATE$")
    _RE_TIME = re.compile(r"TIME$")
    _RE_COUNTER = re.compile(
        r"COUNTER(?:_(?P<name>\w+))?(?:_(?P<action>init|next|get))?(?:_(?P<start>\d+))?$"
    )
    _RE_NEWLINE = re.compile(r"NEWLINE(?:_(?P<count>\d+))?$")
    _RE_TAB = re.compile(r"TAB(?:_(?P<count>\d+))?$")
    _RE_NL = re.compile(r"NL(?:_(?P<count>\d+))?$")

    def __init__(self, strict: bool = False):
        self.strict = strict

    def parse(self, text: str) -> List[Token]:
        tokens: List[Token] = []
        buffer: List[str] = []
        idx, length = 0, len(text)
        # Stack for nested blocks: (type, count, start_idx, extra_data)
        block_stack: List[tuple] = []

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
                    block_stack.append(
                        ("repeat", int(m.group("count")), len(tokens), None)
                    )
                    idx = end_idx + 1
                    continue

                # Check for /REPEAT end
                if self._RE_REPEAT_END.fullmatch(spec.strip()):
                    if block_stack and block_stack[-1][0] == "repeat":
                        _, count, start_idx, _ = block_stack.pop()
                        repeat_tokens = tokens[start_idx:]
                        tokens = tokens[:start_idx]
                        tokens.append(RepeatToken(count, repeat_tokens))
                    idx = end_idx + 1
                    continue

                # Check for LOOP_N start
                m = self._RE_LOOP_START.fullmatch(spec.strip())
                if m:
                    var_name = m.group("var") or "i"
                    block_stack.append(
                        ("loop", int(m.group("count")), len(tokens), var_name)
                    )
                    idx = end_idx + 1
                    continue

                # Check for /LOOP end
                if self._RE_LOOP_END.fullmatch(spec.strip()):
                    if block_stack and block_stack[-1][0] == "loop":
                        _, count, start_idx, var_name = block_stack.pop()
                        loop_tokens = tokens[start_idx:]
                        tokens = tokens[:start_idx]
                        tokens.append(LoopToken(count, loop_tokens, var_name))
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
        """Parse a single spec string and return the corresponding token."""
        # Empty braces means literal {}
        if spec == "":
            return TextToken("{}")

        stripped = spec.strip()

        # Wait
        m = self._RE_WAIT.fullmatch(stripped)
        if m:
            return WaitToken(float(m.group("secs")))

        # Mouse move
        m = self._RE_MOUSE_MOVE.fullmatch(stripped)
        if m:
            return MouseMoveToken(int(m.group("x")), int(m.group("y")))

        # Mouse click
        m = self._RE_MOUSE_CLICK.fullmatch(stripped)
        if m:
            return MouseClickToken(btn=m.group("btn").lower())

        # Random text generation
        m = self._RE_RANDOM.fullmatch(stripped)
        if m:
            length = int(m.group("length"))
            charset = m.group("charset") or "alphanumeric"
            return RandomTextToken(length=length, charset=charset)

        # Variable set
        m = self._RE_VAR_SET.fullmatch(stripped)
        if m:
            return VariableToken(
                name=m.group("name"), value=m.group("value"), action="set"
            )

        # Variable get
        m = self._RE_VAR_GET.fullmatch(stripped)
        if m:
            return VariableToken(name=m.group("name"), action="get")

        # Speed change
        m = self._RE_SPEED.fullmatch(stripped)
        if m:
            speed = float(m.group("speed"))
            variance = float(m.group("variance")) if m.group("variance") else None
            return SpeedToken(speed=speed, variance=variance)

        # DateTime with custom format
        m = self._RE_DATETIME.fullmatch(stripped)
        if m:
            fmt = m.group("format") or "%Y-%m-%d %H:%M:%S"
            return DateTimeToken(format=fmt)

        # Date (shorthand)
        if self._RE_DATE.fullmatch(stripped):
            return DateTimeToken(format="%Y-%m-%d")

        # Time (shorthand)
        if self._RE_TIME.fullmatch(stripped):
            return DateTimeToken(format="%H:%M:%S")

        # Counter
        m = self._RE_COUNTER.fullmatch(stripped)
        if m:
            name = m.group("name") or "default"
            action = m.group("action") or "next"
            start = int(m.group("start")) if m.group("start") else 1
            return CounterToken(name=name, action=action, start=start)

        # Newline
        m = self._RE_NEWLINE.fullmatch(stripped)
        if m:
            count = int(m.group("count")) if m.group("count") else 1
            return NewlineToken(count=count)

        # NL (shorthand for newline)
        m = self._RE_NL.fullmatch(stripped)
        if m:
            count = int(m.group("count")) if m.group("count") else 1
            return NewlineToken(count=count)

        # Tab
        m = self._RE_TAB.fullmatch(stripped)
        if m:
            count = int(m.group("count")) if m.group("count") else 1
            return TabToken(count=count)

        # Key combination
        parts = [p.strip() for p in re.split(r"\s*\+\s*", stripped)]
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
        """Merge consecutive TextTokens for efficiency."""
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
