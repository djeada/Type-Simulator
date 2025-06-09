import sys
import os
from unittest import mock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

with mock.patch.dict('sys.modules', {'pyautogui': mock.MagicMock()}):
    from type_simulator.text_typer import TextTyper


def test_special_keys_mapping():
    typer = TextTyper("")
    keys = typer._get_special_keys()
    assert keys["{ESC}"] == "esc"
    assert keys["{ALT}"] == "alt"
    assert keys["{CTRL}"] == "ctrl"


def test_extract_wait_duration():
    text = "{WAIT_1.5}abc"
    typer = TextTyper(text)
    duration, idx = typer._extract_wait_duration(0)
    assert duration == 1.5
    assert idx == 10


def test_extract_special_key():
    text = "{ESC}abc"
    typer = TextTyper(text)
    key, idx = typer._extract_special_key(0)
    assert key == "{ESC}"
    assert idx == 5
