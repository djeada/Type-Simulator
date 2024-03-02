import subprocess
import sys
import time
import random
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict

import pyautogui


class TypeSimulator:
    def __init__(self,
                 editor_script_path: Optional[str] = None,
                 file_path: Optional[str] = None,
                 text: Optional[str] = None,
                 typing_speed: float = 0.15,
                 typing_variance: float = 0.05):
        pyautogui.FAILSAFE = False
        self.editor_script_path = Path(editor_script_path).resolve() if editor_script_path else None
        self.file_path = Path(file_path).resolve() if file_path else None
        self.text = text
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance

    def run(self):
        try:
            self._open_editor()
            self._load_text()
            self._simulate_typing()
        except Exception as e:
            logging.error(e)
            sys.exit(1)

    def _open_editor(self):
        if self.editor_script_path and not self.editor_script_path.exists():
            raise FileNotFoundError(f"Editor script '{self.editor_script_path}' does not exist.")

        if self.editor_script_path:
            subprocess.Popen([str(self.editor_script_path)])
            time.sleep(2)

    def _load_text(self):
        if self.file_path:
            if not self.file_path.exists():
                raise FileNotFoundError(f"File '{self.file_path}' does not exist.")
            with self.file_path.open('r') as file:
                self.text = file.read()

        if not self.text:
            raise ValueError("No text provided to type.")

    def _simulate_typing(self):
        special_keys = self._get_special_keys()
        i = 0
        while i < len(self.text):
            if self.text[i] == '{':
                special_key, i = self._extract_special_key(i)
                pyautogui.press(special_keys.get(special_key, special_key))
            elif self.text[i] == '\n':
                pyautogui.press('enter')
                i += 1
            else:
                pyautogui.write(self.text[i], interval=self.typing_speed + random.uniform(0, self.typing_variance))
                time.sleep(random.uniform(self.typing_speed, self.typing_speed + self.typing_variance))
                i += 1

    def _get_special_keys(self) -> Dict[str, str]:
        return {
            '{ESC}': 'esc',
            '{ALT}': 'alt',
            '{CTRL}': 'ctrl',
            # Add more mappings as needed
        }

    def _extract_special_key(self, start_index: int) -> (str, int):
        end_index = self.text.find('}', start_index)
        if end_index == -1:
            raise ValueError("Unmatched '{' in text.")
        special_key = self.text[start_index:end_index+1]
        return special_key, end_index + 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Simulate human-like typing in an editor.")
    parser.add_argument("-e", "--editor_script", help="Path to the editor opening script", default=None)
    parser.add_argument("-f", "--file", help="Path to the text file to type", default=None)
    parser.add_argument("-s", "--speed", help="Typing speed in seconds per character", type=float, default=0.15)
    parser.add_argument("-v", "--variance", help="Typing speed variance", type=float, default=0.05)
    parser.add_argument("text", nargs="?", help="Text to type directly", default=None)

    args = parser.parse_args()
    simulator = TypeSimulator(args.editor_script, args.file, args.text, args.speed, args.variance)
    simulator.run()
