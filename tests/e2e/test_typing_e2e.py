import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from difflib import unified_diff
from pathlib import Path

import pytest

TEST_SPEED = 0
TEST_VARIANCE = 0
TIMEOUT = 120  # generous, CI can be slow


# --------------------------------------------------------------------------- #
def load_cases(dir_: Path) -> list[dict]:
    return [
        json.loads((dir_ / f).read_text())
        for f in os.listdir(dir_)
        if f.endswith(".json")
    ]


def pretty_cmd(cmd: list[str]) -> str:
    return " \\\n    ".join(map(str, cmd))


def diff(expected: list[str], got: list[str]) -> str:
    return "\n".join(unified_diff(expected, got, fromfile="expected", tofile="got"))


CASES_DIR = Path(__file__).parent / "cases"


# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", load_cases(CASES_DIR))
def test_typing_case(case):
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        test_file = tmp_dir / "test.txt"
        expected_file = tmp_dir / "expected.txt"
        expected_file.write_text(case["expected"] + "\n")

        cmd = [
            sys.executable,
            "-m",
            "src.main",
            "--file",
            str(test_file),
            "-i",
            case["text"],
            "--speed",
            str(case.get("speed", TEST_SPEED)),
            "--variance",
            str(case.get("variance", TEST_VARIANCE)),
            "--log-level",
            "DEBUG",
        ]

        print("\n" + "=" * 80)
        print(f"🏷️  CASE: {case['name']}")
        print("=" * 80)
        print(textwrap.indent(pretty_cmd(cmd), "🔧 "))

        # Stream child output live
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            print("│ " + line, end="")
        proc.wait(timeout=TIMEOUT)
        assert proc.returncode == 0, "Child process failed"

        # Compare files
        got_lines = test_file.read_text().rstrip("\n").splitlines()
        exp_lines = expected_file.read_text().rstrip("\n").splitlines()

        if got_lines != exp_lines:
            print("❌  Mismatch detected:")
            print(diff(exp_lines, got_lines))
        assert got_lines == exp_lines

        print("✅  Case passed.")

    finally:
        shutil.rmtree(tmp_dir)
