import os
import subprocess
import tempfile
import shutil
import sys
import time
import pexpect

TEST_TEXT = "Hello, E2E test!\nThis is a minimal check."

EDITOR_TIMEOUT = 30  # seconds
TYPER_TIMEOUT = 30   # seconds


def run_vi_with_typing(test_text, test_file):
    print(f"[E2E] Launching vi on {test_file} with pexpect...")
    child = pexpect.spawn(f"vi {test_file}", timeout=EDITOR_TIMEOUT)
    time.sleep(1)  # Give vi time to start
    child.send("i")  # Enter insert mode
    time.sleep(0.5)
    child.send(test_text)
    time.sleep(0.5)
    child.send("\x1b")  # ESC to exit insert mode
    time.sleep(0.5)
    child.send(":wq\r")  # :wq + Enter
    child.expect(pexpect.EOF)
    print("[E2E] vi session complete.")


def main():
    temp_dir = tempfile.mkdtemp()
    try:
        test_file = os.path.join(temp_dir, 'test.txt')
        expected_file = os.path.join(temp_dir, 'expected.txt')
        with open(expected_file, 'w') as f:
            f.write(TEST_TEXT + '\n')

        run_vi_with_typing(TEST_TEXT, test_file)

        # Compare files (ignore trailing blank lines)
        print('[E2E] Comparing files...')
        with open(test_file, 'r') as tf, open(expected_file, 'r') as ef:
            test_lines = [line.rstrip() for line in tf.readlines()]
            expected_lines = [line.rstrip() for line in ef.readlines()]
            # Remove trailing blank lines
            while test_lines and test_lines[-1] == '':
                test_lines.pop()
            while expected_lines and expected_lines[-1] == '':
                expected_lines.pop()
            print('--- test.txt ---')
            print('\n'.join(test_lines))
            print('--- expected.txt ---')
            print('\n'.join(expected_lines))
        if test_lines == expected_lines:
            print('[E2E] PASS: Files match (ignoring trailing blank lines).')
            sys.exit(0)
        else:
            print('[E2E] FAIL: Files differ (ignoring trailing blank lines).')
            for i, (a, b) in enumerate(zip(expected_lines, test_lines)):
                if a != b:
                    print(f'Line {i+1} differs: expected: {a!r}, got: {b!r}')
            if len(expected_lines) != len(test_lines):
                print(f'File lengths differ: expected {len(expected_lines)} lines, got {len(test_lines)} lines')
            sys.exit(1)
    finally:
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    main()
