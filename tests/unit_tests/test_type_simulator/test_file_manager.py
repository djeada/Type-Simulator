import pytest
from type_simulator.file_manager import FileManager
from pathlib import Path
import tempfile


def test_file_manager_create_and_save_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        fm = FileManager(file_path)
        test_content = "Hello, world!"
        fm.save_text(test_content)
        loaded = fm.load_text()
        assert loaded == test_content


def test_file_manager_set_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test2.txt"
        fm = FileManager()
        fm.set_path(file_path)
        fm.save_text("abc")
        assert fm.load_text() == "abc"


def test_file_manager_file_not_found():
    fm = FileManager(create_if_missing=False)
    with pytest.raises(FileNotFoundError):
        fm.load_text()
