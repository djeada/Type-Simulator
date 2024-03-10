import random
import shlex
import subprocess
import time

import pyautogui


class TextTyper:
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
            if char in ["<", ">"]:  # TODO: make it configurable
                self._copy_paste(char)
                time.sleep(self.typing_speed)
                i += 1
            elif char == "{":
                if self.text.startswith("{WAIT_", i):
                    duration, i = self._extract_wait_duration(i)
                    self._wait_for_duration(duration)
                else:
                    # Check if it's a special key
                    end_index = self.text.find("}", i)
                    if end_index == -1:
                        raise ValueError("Unmatched '{' in text.")
                    possible_special_key = self.text[i : end_index + 1]
                    if possible_special_key in self.special_keys:
                        # Handle special key
                        pyautogui.press(self.special_keys[possible_special_key])
                        i = end_index + 1
                    else:
                        # Process unrecognized text character by character
                        while i < end_index:
                            pyautogui.write(
                                self.text[i],
                                interval=self.typing_speed
                                + random.uniform(0, self.typing_variance),
                            )
                            i += 1
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

    def _copy_paste(self, char: str) -> None:
        # Safely quote the character to be echoed
        safe_char = shlex.quote(char)
        # Build the command
        command = f"echo -n {safe_char} | xclip -selection clipboard"  # TODO: make it configurable
        # Execute the command
        subprocess.run(command, shell=True)
        pyautogui.hotkey("ctrl", "shift", "v")  # TODO: make it configurable

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
