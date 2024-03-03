import random
import time

import pyautogui


class TextSimulator:
    def __init__(
        self, text: str, typing_speed: float = 0.05, typing_variance: float = 0.05
    ):
        self.text = text
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance
        self.special_keys = self._get_special_keys()

    def simulate_typing(self):
        i = 0
        while i < len(self.text):
            char = self.text[i]
            if char == "{":
                if self.text.startswith("{WAIT_", i):
                    duration, i = self._extract_wait_duration(i)
                    self._wait_for_duration(duration)
                else:
                    special_key, i = self._extract_special_key(i)
                    pyautogui.press(self.special_keys.get(special_key, special_key))
            elif char == "\n":
                pyautogui.press("enter")
                i += 1
            else:
                pyautogui.write(
                    char,
                    interval=self.typing_speed
                    + random.uniform(0, self.typing_variance),
                )
                time.sleep(
                    random.uniform(
                        self.typing_speed, self.typing_speed + self.typing_variance
                    )
                )
                i += 1

    def _get_special_keys(self) -> dict:
        return {"{ESC}": "esc", "{ALT}": "alt", "{CTRL}": "ctrl"}

    def _extract_wait_duration(self, start_index: int) -> (float, int):
        end_index = self.text.find("}", start_index)
        if end_index == -1:
            raise ValueError("Unmatched '{' in text.")
        wait_sequence = self.text[start_index + 6 : end_index]  # Skip past '{WAIT_'
        duration = float(wait_sequence)
        return duration, end_index + 1

    def _extract_special_key(self, start_index: int) -> (str, int):
        end_index = self.text.find("}", start_index)
        if end_index == -1:
            raise ValueError("Unmatched '{' in text.")
        special_key = self.text[start_index : end_index + 1]
        return special_key, end_index + 1

    def _wait_for_duration(self, duration: float):
        time.sleep(duration)
