import sys
import os
from unittest import mock

with mock.patch.dict("sys.modules", {"pyautogui": mock.MagicMock()}):
    from type_simulator.type_simulator import TypeSimulator, Mode
    from type_simulator.file_manager import FileManager

import tempfile
from pathlib import Path
import io


def test_type_simulator_direct_mode_writes_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "out.txt"
        text = "quick brown fox"
        sim = TypeSimulator(file_path, text, mode=Mode.DIRECT)
        sim.run()
        fm = FileManager(file_path)
        assert fm.load_text() == text


def test_type_simulator_init_modes():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "out2.txt"
        text = "abc"
        # Backwards compatible signature
        sim = TypeSimulator(str(file_path), text, mode=Mode.DIRECT)
        assert sim.mode == Mode.DIRECT
        # New signature
        sim2 = TypeSimulator(file_path, text, mode=Mode.DIRECT)
        assert sim2.mode == Mode.DIRECT


def test_type_simulator_text_from_stdin():
    with mock.patch("sys.stdin", io.StringIO("from stdin")):
        with mock.patch("sys.stdin.isatty", return_value=False):
            simulator = TypeSimulator(text="from arg")
            assert simulator.text == "from stdin"


def test_type_simulator_text_from_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
        tf.write("from file")
        tf.flush()
        simulator = TypeSimulator(text=tf.name)
        assert simulator.text == "from file"
        os.unlink(tf.name)


def test_type_simulator_text_from_nonexistent_file():
    simulator = TypeSimulator(text="/nonexistent/file.txt")
    assert simulator.text == "/nonexistent/file.txt"


def test_type_simulator_text_priority():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
        tf.write("from file")
        tf.flush()
        # Stdin should take precedence over file
        with mock.patch("sys.stdin", io.StringIO("from stdin")):
            with mock.patch("sys.stdin.isatty", return_value=False):
                simulator = TypeSimulator(text=tf.name)
                assert simulator.text == "from stdin"
        os.unlink(tf.name)


def test_direct_mode_expands_macros():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "out.txt"
        text = (
            "{SET_who=World}Hi {GET_who}{NL}{LOOP_3_n}{GET_n}.{TAB}{COUNTER}{NL}{/LOOP}"
        )
        sim = TypeSimulator(file_path, text, mode=Mode.DIRECT)
        sim.run()
        assert file_path.read_text() == "Hi World\n1.\t1\n2.\t2\n3.\t3\n"
        assert sim.rendered_text == file_path.read_text()


def test_direct_mode_ignores_keys_mouse_and_waits():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "out.txt"
        text = "a{WAIT_5}{<ctrl>+c}{MOUSE_MOVE_1_2}{MOUSE_CLICK_left}b{<enter>}c"
        sim = TypeSimulator(file_path, text, mode=Mode.DIRECT)
        sim.run()
        assert file_path.read_text() == "ab\nc"


def test_direct_mode_requires_file_path():
    import pytest

    with pytest.raises(ValueError):
        TypeSimulator(text="hi", mode=Mode.DIRECT)


def test_gui_mode_construction_does_not_init_backend():
    sim = TypeSimulator(text="hello", mode=Mode.GUI, editor_cmd="xterm -e vim")
    assert sim.texter._typist._initialized is False


def test_resolve_text_false_keeps_text_verbatim():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
        tf.write("file content")
    try:
        sim = TypeSimulator(text=tf.name, mode=Mode.FOCUS, resolve_text=False)
        assert sim.text == tf.name
    finally:
        os.unlink(tf.name)
