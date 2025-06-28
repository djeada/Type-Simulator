import pytest
import sys
from unittest import mock

from type_simulator.text_typer.clipboard import PyperclipClipboard, PlatformClipboard, TkClipboard

@pytest.mark.skipif("pyperclip" not in sys.modules and not hasattr(sys, "real_prefix"), reason="pyperclip not installed in test env")
def test_pyperclip_clipboard_copy_paste():
    cb = PyperclipClipboard()
    cb.copy("hello")
    assert cb.paste() == "hello"

def test_platform_clipboard_detect(monkeypatch):
    # Simulate xclip present
    monkeypatch.setattr("shutil.which", lambda cmd: True if cmd == "xclip" else None)
    cmds = PlatformClipboard._detect()
    assert "copy" in cmds and "paste" in cmds

def test_tk_clipboard_copy_paste(monkeypatch):
    # Mock tkinter for headless test
    class DummyTk:
        def __init__(self): self._val = ""
        def withdraw(self): pass
        def clipboard_clear(self): self._val = ""
        def clipboard_append(self, text): self._val += text
        def update(self): pass
        def clipboard_get(self): return self._val
    monkeypatch.setattr("tkinter.Tk", DummyTk)
    import importlib
    importlib.reload(sys.modules["type_simulator.text_typer.clipboard"])
    from type_simulator.text_typer.clipboard import TkClipboard as ReloadedTkClipboard
    cb = ReloadedTkClipboard()
    cb.copy("abc")
    assert cb.paste() == "abc"
