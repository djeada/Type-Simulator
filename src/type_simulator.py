import subprocess
import sys
import time
import random
import logging
from pathlib import Path
from typing import Optional, Dict

import pyautogui


class TypeSimulator:
    def __init__(
        self,
        editor_script_path: Optional[str] = None,
        file_path: Optional[str] = None,
        text: Optional[str] = None,
        typing_speed: float = 0.05,
        typing_variance: float = 0.05,
    ):
        pyautogui.FAILSAFE = False
        self.editor_script_path = (
            Path(editor_script_path).resolve() if editor_script_path else None
        )
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
            raise FileNotFoundError(
                f"Editor script '{self.editor_script_path}' does not exist."
            )

        if self.editor_script_path:
            subprocess.Popen([str(self.editor_script_path)])
            time.sleep(2)

    def _load_text(self):
        if self.file_path:
            if not self.file_path.exists():
                raise FileNotFoundError(f"File '{self.file_path}' does not exist.")
            with self.file_path.open("r") as file:
                self.text = file.read()

        if not self.text:
            raise ValueError("No text provided to type.")

    def _simulate_typing(self):
        special_keys = self._get_special_keys()
        i = 0
        while i < len(self.text):
            if self.text[i] == "{":
                if self.text.startswith("{WAIT_", i):
                    duration, i = self._extract_wait_duration(i)
                    self.wait_for_duration(duration)
                else:
                    special_key, i = self._extract_special_key(i)
                    pyautogui.press(special_keys.get(special_key, special_key))
            elif self.text[i] == "\n":
                pyautogui.press("enter")
                i += 1
            else:
                pyautogui.write(
                    self.text[i],
                    interval=self.typing_speed
                    + random.uniform(0, self.typing_variance),
                )
                time.sleep(
                    random.uniform(
                        self.typing_speed, self.typing_speed + self.typing_variance
                    )
                )
                i += 1

    def _extract_wait_duration(self, start_index: int) -> (float, int):
        end_index = self.text.find("}", start_index)
        if end_index == -1:
            raise ValueError("Unmatched '{' in text.")

        wait_sequence = self.text[start_index + 6:end_index]  # Skip past '{WAIT_'
        duration = float(wait_sequence)
        return duration, end_index + 1

    def wait_for_duration(self, duration: float):
        time.sleep(duration)

    def _get_special_keys(self) -> Dict[str, str]:
        return {
            "{ESC}": "esc",
            "{ALT}": "alt",
            "{CTRL}": "ctrl",
            # Add more mappings as needed
        }

    def _extract_special_key(self, start_index: int) -> (str, int):
        end_index = self.text.find("}", start_index)
        if end_index == -1:
            raise ValueError("Unmatched '{' in text.")
        special_key = self.text[start_index : end_index + 1]
        return special_key, end_index + 1
