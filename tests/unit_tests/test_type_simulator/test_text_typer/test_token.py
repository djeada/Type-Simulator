import pytest
from type_simulator.text_typer.token import TextToken, WaitToken, KeyToken, MouseMoveToken, MouseClickToken

class DummyExecutor:
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

def test_text_token_execute():
    executor = DummyExecutor()
    token = TextToken("Hi")
    token.execute(executor)
    assert executor.actions[0][0] == "write"
    assert executor.actions[0][1] == "H"
    assert executor.actions[1][1] == "i"

def test_wait_token_execute():
    executor = DummyExecutor()
    token = WaitToken(0.01)
    import time
    start = time.time()
    token.execute(executor)
    assert time.time() - start >= 0.01

def test_key_token_execute():
    executor = DummyExecutor()
    token = KeyToken(["ctrl", "c"])
    token.execute(executor)
    assert executor.actions[0] == ("hotkey", ("ctrl", "c"))

def test_mouse_move_token_execute():
    executor = DummyExecutor()
    token = MouseMoveToken(10, 20, duration=0.5)
    token.execute(executor)
    assert executor.actions[0] == ("moveTo", 10, 20, 0.5)

def test_mouse_click_token_execute():
    executor = DummyExecutor()
    token = MouseClickToken(button="right", clicks=2, interval=0.1)
    token.execute(executor)
    assert executor.actions[0] == ("click", "right", 2, 0.1)
