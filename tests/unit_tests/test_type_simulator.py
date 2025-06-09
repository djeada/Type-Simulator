import sys
import os
from unittest import mock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

with mock.patch.dict('sys.modules', {'pyautogui': mock.MagicMock()}):
    from type_simulator.type_simulator import TypeSimulator, Mode
    from type_simulator.file_manager import FileManager

import tempfile
from pathlib import Path


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
