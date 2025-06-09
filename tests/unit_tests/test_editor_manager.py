import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from type_simulator.editor_manager import EditorManager


def test_editor_manager_default_cmd():
    em = EditorManager()
    assert em.editor_cmd == EditorManager.DEFAULT_CMD


def test_editor_manager_custom_cmd():
    em = EditorManager("nano")
    assert em.editor_cmd == "nano"
