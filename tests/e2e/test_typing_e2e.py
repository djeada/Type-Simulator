# tests/e2e/test_typing_e2e.py
import os
import subprocess
import tempfile
import shutil
import sys
import json

TEST_SPEED = 0
TEST_VARIANCE = 0
TIMEOUT = 30  # seconds

def load_test_cases(cases_dir):
    cases = []
    for fname in os.listdir(cases_dir):
        if fname.endswith(".json"):
            with open(os.path.join(cases_dir, fname), "r") as f:
                cases.append(json.load(f))
    return cases

def main():
    cases_dir = os.path.join(os.path.dirname(__file__), "cases")
    cases = load_test_cases(cases_dir)
    all_passed = True

    for case in cases:
        print(f"\n=== Running E2E case: {case['name']} ===")
        temp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(temp_dir, "test.txt")
            expected_file = os.path.join(temp_dir, "expected.txt")
            with open(expected_file, "w") as f:
                f.write(case["expected"] + "\n")

            # Build the command under a throw-away X server
            base_cmd = [
                sys.executable, "-m", "src.main",
                "--file", test_file,
                "--text", case["text"],
                "--speed", str(case.get("speed", TEST_SPEED)),
                "--variance", str(case.get("variance", TEST_VARIANCE)),
            ]
            full_cmd = [
                "xvfb-run",
                "--auto-servernum",
                "--server-args=-screen 0 1024x768x16 -ac",
            ] + base_cmd

            print(f"[E2E] Running: {' '.join(full_cmd)}")
            subprocess.run(full_cmd, timeout=TIMEOUT, check=True)

            # Compare files (ignore trailing blank lines)
            with open(test_file, "r") as tf, open(expected_file, "r") as ef:
                test_lines = [line.rstrip() for line in tf]
                expected_lines = [line.rstrip() for line in ef]
                while test_lines and test_lines[-1] == "":
                    test_lines.pop()
                while expected_lines and expected_lines[-1] == "":
                    expected_lines.pop()

            if test_lines == expected_lines:
                print(f"[E2E] PASS: {case['name']}")
            else:
                print(f"[E2E] FAIL: {case['name']}")
                for i, (exp, got) in enumerate(zip(expected_lines, test_lines), start=1):
                    if exp != got:
                        print(f"Line {i} differs: expected {exp!r}, got {got!r}")
                if len(expected_lines) != len(test_lines):
                    print(f"Length mismatch: expected {len(expected_lines)} lines, got {len(test_lines)} lines")
                all_passed = False

        finally:
            shutil.rmtree(temp_dir)

    if all_passed:
        print("\nALL E2E TESTS PASSED")
        sys.exit(0)
    else:
        print("\nSOME E2E TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
