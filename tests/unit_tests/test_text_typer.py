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


# Dummy backend to capture actions
class DummyBackend:
    def __init__(self):
        self.actions = []

    def write(self, ch, interval=None):
        self.actions.append(("write", ch, interval))

    def hotkey(self, *keys):
        self.actions.append(("hotkey", keys))


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


# Typist tests


def test_typist_execute_text_and_keys():
    backend = DummyBackend()
    typist = Typist(typing_speed=0.01, typing_variance=0, backend=backend)
    tokens = [TextToken("AB"), KeyToken(["ctrl", "c"]), TextToken("CD")]
    typist.execute(tokens)
    # Expect writes, hotkey, then writes
    assert backend.actions[2] == ("hotkey", ("ctrl", "c"))


def test_typist_execute_wait():
    backend = DummyBackend()
    typist = Typist(backend=backend)
    start = time.time()
    typist.execute([WaitToken(0.01)])
    assert time.time() - start >= 0.01


# Integration tests


def test_text_typer_integration():
    backend = DummyBackend()
    typer = TextTyper(
        "Hi{<enter>}!", typing_speed=0, typing_variance=0, backend=backend
    )
    typer.simulate_typing()
    expected = [
        ("write", "H", 0),
        ("write", "i", 0),
        ("hotkey", ("enter",)),
        ("write", "!", 0),
    ]
    assert backend.actions == expected


def test_text_typer_escape_and_wait(caplog):
    caplog.set_level(logging.WARNING)
    backend = DummyBackend()
    typer = TextTyper(
        r"\\{Wait\\}{WAIT_0.01}", typing_speed=0, typing_variance=0, backend=backend
    )
    start = time.time()
    typer.simulate_typing()
    duration = time.time() - start
    # First action should write literal '{'
    assert backend.actions[0] == ("write", "{", 0)
    # Then a wait occurred for at least 0.01s
    assert duration >= 0.01
