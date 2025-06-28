import pytest
import os
import time
import logging

from type_simulator.text_typer.token import TextToken, WaitToken, KeyToken
from type_simulator.text_typer.parser import CommandParser
from type_simulator.text_typer.__main__ import Typist, TextTyper


# Dummy backend to capture actions
class DummyBackend:
    def __init__(self):
        self.actions = []

    def write(self, ch, interval=None):
        self.actions.append(("write", ch, interval))

    def hotkey(self, *keys):
        self.actions.append(("hotkey", keys))


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
    # The actual output may use paste for '!' due to PROBLEMATIC_CHARS, so check the sequence more flexibly
    expected = [
        ("write", "H", 0),
        ("write", "i", 0),
        ("hotkey", ("enter",)),
    ]
    # The last action can be either a write or a hotkey paste for '!'
    assert backend.actions[:3] == expected
    # Accept either a write or a hotkey for the last action
    last_action = backend.actions[3]
    assert (last_action[0] == "write" and last_action[1] == "!") or (
        last_action[0] == "hotkey" and "insert" in last_action[1]
    )


def test_text_typer_escape_and_wait(caplog):
    caplog.set_level(logging.WARNING)
    backend = DummyBackend()
    typer = TextTyper(
        r"\\{Wait\\}{WAIT_0.01}", typing_speed=0, typing_variance=0, backend=backend
    )
    start = time.time()
    typer.simulate_typing()
    duration = time.time() - start
    # The first action can be a write or a hotkey paste for '\'
    first_action = backend.actions[0]
    assert (first_action[0] == "write" and first_action[1] == "\\") or (
        first_action[0] == "hotkey" and "insert" in first_action[1]
    )
    # Then a wait occurred for at least 0.01s
    assert duration >= 0.01
