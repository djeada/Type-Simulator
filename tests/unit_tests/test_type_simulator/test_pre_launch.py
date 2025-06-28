from unittest import mock

with mock.patch.dict("sys.modules", {"pyautogui": mock.MagicMock()}):
    from type_simulator.type_simulator import TypeSimulator, Mode

import pytest
import subprocess
from pathlib import Path
import tempfile


def test_pre_launch_command_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        sim = TypeSimulator(
            file_path,
            "test",
            mode=Mode.DIRECT,
            pre_launch_cmd="echo 'test' > /dev/null",
        )
        sim.run()  # Should not raise


def test_pre_launch_command_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        sim = TypeSimulator(
            file_path, "test", mode=Mode.DIRECT, pre_launch_cmd="nonexistent-command"
        )
        with pytest.raises(RuntimeError, match="Pre-launch command failed"):
            sim.run()


def test_no_pre_launch_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        sim = TypeSimulator(file_path, "test", mode=Mode.DIRECT)
        sim.run()  # Should not raise


@mock.patch("subprocess.run")
def test_pre_launch_command_called_correctly(mock_run):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        test_cmd = "echo 'test'"
        sim = TypeSimulator(
            file_path, "test", mode=Mode.DIRECT, pre_launch_cmd=test_cmd
        )
        sim.run()

        # Verify subprocess.run was called correctly
        mock_run.assert_called_once_with(test_cmd, shell=True, check=True)
