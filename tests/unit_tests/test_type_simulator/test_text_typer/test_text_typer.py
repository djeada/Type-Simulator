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
        self.typing_speed = 0
        self.typing_variance = 0
        self.backend = self
        self.clipboard = None
        self.pynput = None

    def write(self, ch, interval=None):
        self.actions.append(("write", ch, interval))

    def hotkey(self, *keys):
        self.actions.append(("hotkey", keys))

    def moveTo(self, x, y, duration=0):
        self.actions.append(("moveTo", x, y, duration))

    def click(self, button="left", clicks=1, interval=0):
        self.actions.append(("click", button, clicks, interval))

    def press(self, key):
        self.actions.append(("press", key))


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
    ]
    assert backend.actions[:3] == expected
    last_action = backend.actions[3]
    # Accept write, hotkey with 'insert', or hotkey with ctrl+shift+u (unicode hex fallback)
    assert (last_action[0] == "write" and last_action[1] == "!") or (
        last_action[0] == "hotkey"
        and (
            "insert" in last_action[1]
            or (
                "ctrl" in last_action[1]
                and "shift" in last_action[1]
                and "u" in last_action[1]
            )
        )
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
    first_action = backend.actions[0]
    assert (first_action[0] == "write" and first_action[1] == "\\") or (
        first_action[0] == "hotkey"
        and (
            "insert" in first_action[1]
            or (
                "ctrl" in first_action[1]
                and "shift" in first_action[1]
                and "u" in first_action[1]
            )
        )
    )
    assert duration >= 0.01


def test_render_expands_counter_init():
    typer = TextTyper(
        "{COUNTER_x_init_5}{COUNTER_x} {COUNTER_x} {COUNTER_x_get}", lazy_init=True
    )
    assert typer.render() == "5 6 6"


def test_render_does_not_touch_gui_backend():
    typer = TextTyper("a{NL}b", lazy_init=True)
    assert typer.render() == "a\nb"
    assert typer._typist._initialized is False


def test_profile_pause_triggers_between_words(monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
    backend = DummyBackend()
    typist = Typist(0, 0, backend=backend, pause_probability=1.0, pause_duration=0.2)
    typist.execute([TextToken("a b c")])
    pauses = [s for s in sleeps if s > 0]
    assert len(pauses) == 2
    assert all(0.1 <= s <= 0.3 for s in pauses)


def test_strict_typist_propagates_errors():
    class Boom(TextToken):
        def execute(self, executor):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        Typist(backend=DummyBackend(), strict=True).execute([Boom("x")])
    Typist(backend=DummyBackend(), strict=False).execute([Boom("x")])
