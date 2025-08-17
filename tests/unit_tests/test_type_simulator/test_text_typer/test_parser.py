import pytest
import os
import time
import logging

from type_simulator.text_typer.token import TextToken, WaitToken, KeyToken
from type_simulator.text_typer.parser import CommandParser
from type_simulator.text_typer.__main__ import Typist, TextTyper


# Parser tests


def test_parse_plain_text():
    parser = CommandParser()
    tokens = parser.parse("Hello")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "Hello"


def test_parse_literal_braces():
    parser = CommandParser()
    tokens = parser.parse(r"Text \{braces\}")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "Text {braces}"


def test_parse_wait_token():
    parser = CommandParser()
    tokens = parser.parse("A{WAIT_2}B")
    # The parser merges text tokens, so expect: [TextToken('A'), WaitToken(2.0), TextToken('B')]
    assert len(tokens) == 3
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "A"
    assert type(tokens[1]).__name__ == "WaitToken"
    assert getattr(tokens[1], "seconds", None) == pytest.approx(2.0)
    assert type(tokens[2]).__name__ == "TextToken"
    assert getattr(tokens[2], "text", None) == "B"


def test_parse_key_token_single():
    parser = CommandParser()
    tokens = parser.parse("X{<esc>}Y")
    assert type(tokens[1]).__name__ == "KeyToken"
    assert getattr(tokens[1], "keys", None) == ["esc"]


def test_parse_key_token_combo_whitespace():
    parser = CommandParser()
    tokens = parser.parse("{ <ctrl> + <alt> + t }")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "KeyToken"
    assert getattr(tokens[0], "keys", None) == ["ctrl", "alt", "t"]


def test_parse_invalid_sequence_skips(caplog):
    caplog.set_level(logging.WARNING)
    parser = CommandParser()
    tokens = parser.parse("A{INVALID_KEY}B")
    # The parser treats invalid sequences as literal text, so expect one TextToken with the full string
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "A{INVALID_KEY}B"
    # The parser logs a warning only in strict mode, so this may not always be present
    # assert "Skipping invalid sequence" in caplog.text


def test_preserve_angle_bracket():
    parser = CommandParser()
    # Beginning
    tokens = parser.parse("<abc")
    assert len(tokens) == 1
    assert type(tokens[0]).__name__ == "TextToken"
    assert getattr(tokens[0], "text", None) == "<abc"
    # Middle
    tokens = parser.parse("a < b")
    assert len(tokens) == 1
    assert getattr(tokens[0], "text", None) == "a < b"
    # End
    tokens = parser.parse("abc<")
    assert len(tokens) == 1
    assert getattr(tokens[0], "text", None) == "abc<"
    # Multiple
    tokens = parser.parse("<a < b<")
    assert len(tokens) == 1
    assert getattr(tokens[0], "text", None) == "<a < b<"


def test_preserve_colon():
    parser = CommandParser()
    # Key-value
    tokens = parser.parse("Key: Value")
    assert len(tokens) == 1
    assert tokens[0].text == "Key: Value"
    # Timestamp
    tokens = parser.parse("12:30")
    assert len(tokens) == 1
    assert tokens[0].text == "12:30"
    # Multiple colons
    tokens = parser.parse("a:b:c")
    assert len(tokens) == 1
    assert tokens[0].text == "a:b:c"
    # Colon at start/end
    tokens = parser.parse(":start and end:")
    assert len(tokens) == 1
    assert tokens[0].text == ":start and end:"


def test_preserve_empty_lines_after_brace_and_logging(caplog):
    """Ensure that empty lines after '{' are preserved and visible in logs when invalid spec occurs."""
    caplog.set_level(logging.DEBUG)
    parser = CommandParser(strict=False)
    text = "{\n\nint value = 1;\n}"
    tokens = parser.parse(text)
    assert len(tokens) == 1
    assert isinstance(tokens[0], TextToken)
    assert tokens[0].text.startswith("{\n\nint value")

    # Now with strict=True and an invalid spec that includes newlines to check escaped logging
    caplog.clear()
    parser_strict = CommandParser(strict=True)
    bad = "{INVALID\n\nSPEC}"
    tokens2 = parser_strict.parse(bad)
    # In strict mode, invalid is skipped; result is empty text token list
    assert all(t.__class__.__name__ != 'TextToken' or t.text != bad for t in tokens2)
    # Ensure the log contains the escaped \n sequences
    assert "Invalid sequence '{INVALID\\n\\nSPEC}'" in caplog.text
