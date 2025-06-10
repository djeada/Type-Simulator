import sys
import os
import platform
import pytest
from unittest import mock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

with mock.patch.dict("sys.modules", {"pyautogui": mock.MagicMock()}):
    from type_simulator.type_simulator import TypeSimulator, Mode
    from utils.utils import get_focus_mode_dependency


@pytest.fixture
def mock_platform(monkeypatch):
    def mock_system():
        return "Linux"

    monkeypatch.setattr(platform, "system", mock_system)
    return mock_system


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    calls = []

    def fake_run(cmd, check=False):
        calls.append({"cmd": cmd, "check": check})
        return mock.MagicMock()

    monkeypatch.setattr("subprocess.run", fake_run)
    return calls


def test_focus_mode_basic(mock_platform, mock_subprocess_run):
    """Test basic focus mode functionality with simple text."""
    # Mock xdotool as installed
    with mock.patch("utils.utils.is_program_installed", return_value=True):
        sim = TypeSimulator(text="Hello focus!", mode=Mode.FOCUS)
        sim.run()

        assert len(mock_subprocess_run) > 0
        assert mock_subprocess_run[0]["cmd"][0] == "xdotool"
        assert "Hello focus!" in mock_subprocess_run[0]["cmd"]
        assert mock_subprocess_run[0]["check"] is True


def test_focus_mode_multiline(mock_platform, mock_subprocess_run):
    """Test focus mode with multiline text."""
    with mock.patch("utils.utils.is_program_installed", return_value=True):
        sim = TypeSimulator(text="Line 1\\nLine 2", mode=Mode.FOCUS)
        sim.run()

        # Should see multiple commands: type first line, press return, type second line
        assert len(mock_subprocess_run) >= 3
        assert "Line 1" in mock_subprocess_run[0]["cmd"]
        assert "Return" in mock_subprocess_run[1]["cmd"]
        assert "Line 2" in mock_subprocess_run[2]["cmd"]


def test_focus_mode_no_text():
    """Test focus mode fails appropriately with no text."""
    with mock.patch("utils.utils.is_program_installed", return_value=True):
        with pytest.raises(ValueError, match="No text provided"):
            sim = TypeSimulator(mode=Mode.FOCUS)
            sim.run()


def test_focus_mode_missing_dependency(mock_platform, monkeypatch):
    """Test focus mode fails appropriately when required tool is missing."""

    def mock_is_installed(program):
        return False

    monkeypatch.setattr("utils.utils.is_program_installed", mock_is_installed)

    with pytest.raises(RuntimeError, match="Required tool.*not installed"):
        sim = TypeSimulator(text="test", mode=Mode.FOCUS)
        sim.run()


@pytest.mark.parametrize("system", ["Linux", "Darwin", "Windows"])
def test_focus_mode_cross_platform(monkeypatch, system):
    """Test focus mode initialization across different platforms."""

    def mock_system():
        return system

    monkeypatch.setattr(platform, "system", mock_system)

    # Mock platform-specific dependencies
    dependency = get_focus_mode_dependency(system)
    if dependency:

        def mock_is_installed(program):
            return True

        monkeypatch.setattr("utils.utils.is_program_installed", mock_is_installed)

    # Should initialize without errors
    sim = TypeSimulator(text="test", mode=Mode.FOCUS)
    assert sim.mode == Mode.FOCUS
