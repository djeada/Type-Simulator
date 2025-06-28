import pytest
import sys
import os
import time
import logging

# Adjust path to import our module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from type_simulator.text_typer import (
    CommandParser,
    Typist,
    TextTyper,
    TextToken,
    WaitToken,
    KeyToken,
)


# Parser tests


def test_parse_plain_text():
    parser = CommandParser()
    tokens = parser.parse("Hello")
    assert len(tokens) == 1
    assert isinstance(tokens[0], TextToken)
    assert tokens[0].text == "Hello"


def test_parse_literal_braces():
    parser = CommandParser()
    tokens = parser.parse(r"Text \{braces\}")
    assert len(tokens) == 1
    assert isinstance(tokens[0], TextToken)
    assert tokens[0].text == "Text {braces}"


def test_parse_wait_token():
    parser = CommandParser()
    tokens = parser.parse("A{WAIT_2}B")
    assert isinstance(tokens[0], TextToken)
    assert isinstance(tokens[1], WaitToken)
    assert tokens[1].duration == pytest.approx(2.0)
    assert isinstance(tokens[2], TextToken)
    assert tokens[2].text == "B"


def test_parse_key_token_single():
    parser = CommandParser()
    tokens = parser.parse("X{<esc>}Y")
    assert isinstance(tokens[1], KeyToken)
    assert tokens[1].keys == ["esc"]


def test_parse_key_token_combo_whitespace():
    parser = CommandParser()
    tokens = parser.parse("{ <ctrl> + <alt> + t }")
    assert len(tokens) == 1
    assert isinstance(tokens[0], KeyToken)
    assert tokens[0].keys == ["ctrl", "alt", "t"]


def test_parse_invalid_sequence_skips(caplog):
    caplog.set_level(logging.WARNING)
    parser = CommandParser()
    tokens = parser.parse("A{INVALID_KEY}B")
    # Invalid sequence should be skipped, merging A and B
    assert len(tokens) == 1
    assert isinstance(tokens[0], TextToken)
    assert tokens[0].text == "AB"
    assert "Skipping invalid sequence" in caplog.text


def test_preserve_angle_bracket():
    parser = CommandParser()
    # Beginning
    tokens = parser.parse("<abc")
    assert len(tokens) == 1
    assert isinstance(tokens[0], TextToken)
    assert tokens[0].text == "<abc"
    # Middle
    tokens = parser.parse("a < b")
    assert len(tokens) == 1
    assert tokens[0].text == "a < b"
    # End
    tokens = parser.parse("abc<")
    assert len(tokens) == 1
    assert tokens[0].text == "abc<"
    # Multiple
    tokens = parser.parse("<a < b<")
    assert len(tokens) == 1
    assert tokens[0].text == "<a < b<"


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
