import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from utils.utils import is_program_installed, install_instructions


def test_is_program_installed_true():
    # 'python3' should be present on most systems running these tests
    assert is_program_installed("python3")


def test_is_program_installed_false():
    assert not is_program_installed("definitelynotarealprogram123")


def test_install_instructions_known():
    assert "xclip" in install_instructions("xclip")
    assert "pip install pyautogui" in install_instructions("pyautogui")


def test_install_instructions_unknown():
    assert install_instructions("foobar") == "No installation instructions available for foobar."
