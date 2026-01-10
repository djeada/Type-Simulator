import pytest
from utils.utils import is_program_installed, install_instructions, get_default_terminal_command
from unittest.mock import patch


def test_is_program_installed_true():
    # 'python3' should be present on most systems running these tests
    assert is_program_installed("python3")


def test_is_program_installed_false():
    assert not is_program_installed("definitelynotarealprogram123")


def test_install_instructions_known():
    assert "xclip" in install_instructions("xclip")
    assert "pip install pyautogui" in install_instructions("pyautogui")


def test_install_instructions_unknown():
    assert (
        install_instructions("foobar")
        == "No installation instructions available for foobar."
    )


def test_get_default_terminal_command_linux_gnome():
    """Test that gnome-terminal is detected on Linux."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/gnome-terminal" if x == "gnome-terminal" else None
            cmd, error = get_default_terminal_command()
            assert cmd == "gnome-terminal -- bash"
            assert error is None


def test_get_default_terminal_command_linux_konsole():
    """Test that konsole is detected on Linux when gnome-terminal is not available."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            def which_side_effect(x):
                if x == "konsole":
                    return "/usr/bin/konsole"
                return None
            mock_which.side_effect = which_side_effect
            cmd, error = get_default_terminal_command()
            assert cmd == "konsole -e bash"
            assert error is None


def test_get_default_terminal_command_linux_xterm_fallback():
    """Test that xterm is used as fallback on Linux."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            def which_side_effect(x):
                if x == "xterm":
                    return "/usr/bin/xterm"
                return None
            mock_which.side_effect = which_side_effect
            cmd, error = get_default_terminal_command()
            assert cmd == "xterm -e bash"
            assert error is None


def test_get_default_terminal_command_linux_no_terminal():
    """Test that an error is returned when no terminal is found on Linux."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which", return_value=None):
            cmd, error = get_default_terminal_command()
            assert cmd is None
            assert "No terminal emulator found" in error
            assert "gnome-terminal" in error


def test_get_default_terminal_command_macos():
    """Test that 'open -a Terminal' is used on macOS."""
    with patch("platform.system", return_value="Darwin"):
        cmd, error = get_default_terminal_command()
        assert cmd == "open -a Terminal"
        assert error is None


def test_get_default_terminal_command_windows():
    """Test that cmd.exe is used on Windows."""
    with patch("platform.system", return_value="Windows"):
        cmd, error = get_default_terminal_command()
        assert cmd == "cmd.exe /k"
        assert error is None


def test_get_default_terminal_command_unsupported():
    """Test that an error is returned for unsupported platforms."""
    with patch("platform.system", return_value="UnknownOS"):
        cmd, error = get_default_terminal_command()
        assert cmd is None
        assert "Unsupported platform" in error
