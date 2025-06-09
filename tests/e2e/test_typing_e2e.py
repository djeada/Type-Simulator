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
            f.write(TEST_TEXT)

        run_vi_with_typing(TEST_TEXT, test_file)

        # Compare files
        print('[E2E] Comparing files...')
        with open(test_file, 'r') as tf, open(expected_file, 'r') as ef:
            print('--- test.txt ---')
            print(tf.read())
            print('--- expected.txt ---')
            print(ef.read())
        result = subprocess.run(['diff', '-u', expected_file, test_file], capture_output=True)
        if result.returncode == 0:
            print('[E2E] PASS: Files match.')
            sys.exit(0)
        else:
            print('[E2E] FAIL: Files differ.')
            print(result.stdout.decode())
            sys.exit(1)
    finally:
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    main()
