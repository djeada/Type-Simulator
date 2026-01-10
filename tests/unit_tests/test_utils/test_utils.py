import pytest
from utils.utils import is_program_installed, install_instructions, get_default_terminal_command, check_terminal_availability
from unittest.mock import patch
import io
import sys


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


def test_check_terminal_availability_linux_with_gnome():
    """Test check_terminal_availability on Linux with gnome-terminal."""
    with patch("utils.utils.platform.system", return_value="Linux"):
        with patch("utils.utils.shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/gnome-terminal" if x == "gnome-terminal" else None
            # Capture stdout
            captured = io.StringIO()
            sys.stdout = captured
            try:
                available, unavailable = check_terminal_availability()
            finally:
                sys.stdout = sys.__stdout__
            
            output = captured.getvalue()
            assert "gnome-terminal" in output
            assert "✅" in output
            assert len(available) == 1
            assert available[0][0] == "gnome-terminal"


def test_check_terminal_availability_linux_no_terminals():
    """Test check_terminal_availability on Linux with no terminals."""
    with patch("utils.utils.platform.system", return_value="Linux"):
        with patch("utils.utils.shutil.which", return_value=None):
            captured = io.StringIO()
            sys.stdout = captured
            try:
                available, unavailable = check_terminal_availability()
            finally:
                sys.stdout = sys.__stdout__
            
            output = captured.getvalue()
            assert "No terminal emulators found" in output
            assert len(available) == 0
            assert len(unavailable) == 8  # All 8 Linux terminals


def test_check_terminal_availability_macos():
    """Test check_terminal_availability on macOS."""
    with patch("utils.utils.platform.system", return_value="Darwin"):
        with patch("utils.utils.shutil.which", return_value=None):  # No iTerm
            captured = io.StringIO()
            sys.stdout = captured
            try:
                available, unavailable = check_terminal_availability()
            finally:
                sys.stdout = sys.__stdout__
            
            output = captured.getvalue()
            assert "macOS detected" in output
            assert "Terminal.app is built-in" in output
            assert ("Terminal.app", "Built-in") in available


def test_check_terminal_availability_windows():
    """Test check_terminal_availability on Windows."""
    with patch("utils.utils.platform.system", return_value="Windows"):
        with patch("utils.utils.shutil.which", return_value=None):  # No WT or pwsh
            captured = io.StringIO()
            sys.stdout = captured
            try:
                available, unavailable = check_terminal_availability()
            finally:
                sys.stdout = sys.__stdout__
            
            output = captured.getvalue()
            assert "Windows detected" in output
            assert "cmd.exe is built-in" in output
            assert ("cmd.exe", "Built-in") in available


def test_get_default_terminal_command_with_geometry_gnome():
    """Test that geometry is applied to gnome-terminal on Linux."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/gnome-terminal" if x == "gnome-terminal" else None
            cmd, error = get_default_terminal_command(geometry="80x24")
            assert cmd == "gnome-terminal --geometry=80x24 -- bash"
            assert error is None


def test_get_default_terminal_command_with_geometry_xterm():
    """Test that geometry is applied to xterm on Linux."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            def which_side_effect(x):
                if x == "xterm":
                    return "/usr/bin/xterm"
                return None
            mock_which.side_effect = which_side_effect
            cmd, error = get_default_terminal_command(geometry="100x40")
            assert cmd == "xterm -geometry 100x40 -e bash"
            assert error is None


def test_get_default_terminal_command_with_geometry_xfce4():
    """Test that geometry is applied to xfce4-terminal on Linux."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            def which_side_effect(x):
                if x == "xfce4-terminal":
                    return "/usr/bin/xfce4-terminal"
                return None
            mock_which.side_effect = which_side_effect
            cmd, error = get_default_terminal_command(geometry="120x30")
            assert cmd == "xfce4-terminal --geometry=120x30 -e bash"
            assert error is None


def test_get_default_terminal_command_geometry_not_used_on_macos():
    """Test that geometry parameter is ignored on macOS."""
    with patch("platform.system", return_value="Darwin"):
        cmd, error = get_default_terminal_command(geometry="80x24")
        # macOS doesn't support geometry in Terminal.app command
        assert cmd == "open -a Terminal"
        assert error is None


def test_get_default_terminal_command_geometry_not_used_on_windows():
    """Test that geometry parameter is ignored on Windows."""
    with patch("platform.system", return_value="Windows"):
        cmd, error = get_default_terminal_command(geometry="80x24")
        # Windows cmd.exe doesn't support geometry via command line
        assert cmd == "cmd.exe /k"
        assert error is None


def test_get_default_terminal_command_without_geometry():
    """Test that terminals without geometry support fall back to default command."""
    with patch("platform.system", return_value="Linux"):
        with patch("shutil.which") as mock_which:
            def which_side_effect(x):
                # konsole doesn't have geometry in our template
                if x == "konsole":
                    return "/usr/bin/konsole"
                return None
            mock_which.side_effect = which_side_effect
            cmd, error = get_default_terminal_command(geometry="80x24")
            # konsole's geometry template doesn't have {geometry} placeholder
            assert cmd == "konsole -e bash"
            assert error is None
