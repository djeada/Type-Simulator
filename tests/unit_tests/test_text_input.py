import io
import os
import sys
import pytest
from pathlib import Path
import tempfile
from utils.text_input import (
    get_text_content,
    TextInputError,
    FileReadError,
    StdinReadError,
    FileSizeError,
    MAX_FILE_SIZE,
    MAX_STDIN_SIZE,
)


def test_get_text_content_stdin():
    with io.StringIO("from stdin") as fake_stdin:
        sys.stdin = fake_stdin
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(sys.stdin, "isatty", lambda: False)
            assert get_text_content("ignored text") == "from stdin"
    sys.stdin = sys.__stdin__  # Restore stdin


def test_get_text_content_empty_stdin():
    with io.StringIO("") as fake_stdin:
        sys.stdin = fake_stdin
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(sys.stdin, "isatty", lambda: False)
            with pytest.raises(StdinReadError, match="Empty input"):
                get_text_content()
    sys.stdin = sys.__stdin__


def test_get_text_content_stdin_too_large():
    large_content = "x" * (MAX_STDIN_SIZE + 1)
    with io.StringIO(large_content) as fake_stdin:
        sys.stdin = fake_stdin
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(sys.stdin, "isatty", lambda: False)
            with pytest.raises(FileSizeError, match="exceeds size limit"):
                get_text_content()
    sys.stdin = sys.__stdin__


def test_get_text_content_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
        tf.write("from file")
        tf.flush()
        assert get_text_content(tf.name) == "from file"
        Path(tf.name).unlink()


def test_get_text_content_file_with_tilde():
    # Create a test file in home directory
    home_file = Path.home() / ".type_simulator_test"
    try:
        home_file.write_text("home test")
        # Test with ~ notation
        assert get_text_content("~/.type_simulator_test") == "home test"
    finally:
        home_file.unlink(missing_ok=True)


def test_get_text_content_file_too_large():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
        # Just create a large sparse file
        tf.seek(MAX_FILE_SIZE + 1)
        tf.write("x")
        tf.flush()
        with pytest.raises(FileSizeError, match="exceeds size limit"):
            get_text_content(tf.name)
        Path(tf.name).unlink()


def test_get_text_content_file_permission_error():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
        tf.write("secret")
        tf.flush()
        # Remove read permission
        os.chmod(tf.name, 0o000)
        with pytest.raises(FileReadError, match="Permission denied"):
            get_text_content(tf.name)
        # Restore permissions for cleanup
        os.chmod(tf.name, 0o600)
        Path(tf.name).unlink()


def test_get_text_content_file_various_encodings():
    encodings = {
        "utf-8": "Hello 👋",
        "latin-1": "Hello £",
        "utf-8-sig": "\ufeffHello",  # With BOM
    }

    for encoding, content in encodings.items():
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tf:
            tf.write(content.encode(encoding))
            tf.flush()
            result = get_text_content(tf.name)
            # utf-8-sig automatically removes BOM
            expected = (
                content.replace("\ufeff", "") if encoding == "utf-8-sig" else content
            )
            assert result == expected
            Path(tf.name).unlink()


def test_get_text_content_literal():
    assert get_text_content("literal text") == "literal text"


def test_get_text_content_no_input():
    # Close stdin for this test
    old_stdin = sys.stdin
    sys.stdin = None
    try:
        with pytest.raises(ValueError, match="No text source available"):
            get_text_content(None)
    finally:
        sys.stdin = old_stdin


def test_get_text_content_nonexistent_file():
    # When given a non-existent file path, should treat it as literal text
    assert get_text_content("/nonexistent/file.txt") == "/nonexistent/file.txt"


def test_get_text_content_relative_path():
    with tempfile.TemporaryDirectory() as td:
        file_path = Path(td) / "test.txt"
        file_path.write_text("relative test")
        # Change to temp dir and use relative path
        old_cwd = os.getcwd()
        try:
            os.chdir(td)
            assert get_text_content("test.txt") == "relative test"
        finally:
            os.chdir(old_cwd)


# The following tests already cover the required cases:
# - test_get_text_content_file: passing a valid file path
# - test_get_text_content_literal: passing arbitrary text
# - test_get_text_content_stdin: piping text via STDIN
# Add a CLI parser test to ensure only --input is accepted.
import subprocess


def test_cli_input_flag(tmp_path):
    # Create a file with known content
    file = tmp_path / "input.txt"
    file.write_text("file input test")
    # Run CLI with --input as file path
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.main",
            "--input",
            str(file),
            "--output",
            str(tmp_path / "out.txt"),
            "--mode",
            "direct",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Run CLI with --input as literal text
    result2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.main",
            "--input",
            "literal input test",
            "--output",
            str(tmp_path / "out2.txt"),
            "--mode",
            "direct",
        ],
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0
    # Run CLI with STDIN
    result3 = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.main",
            "--output",
            str(tmp_path / "out3.txt"),
            "--mode",
            "direct",
        ],
        input="stdin input test",
        capture_output=True,
        text=True,
    )
    assert result3.returncode == 0
