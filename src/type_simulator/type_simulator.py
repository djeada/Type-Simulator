import logging
import sys
from typing import Optional

import pyautogui

from src.type_simulator.editor_manager import EditorManager
from src.type_simulator.file_manager import FileManager
from src.type_simulator.text_simulator import TextSimulator


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
        self.editor_manager = EditorManager(editor_script_path)
        self.file_manager = FileManager(file_path)
        self.text = text
        self.text_simulator = TextSimulator(text, typing_speed, typing_variance)

    def run(self):
        try:
            self.editor_manager.open_editor()
            if not self.text:
                self.text = self.file_manager.load_text()
            self.text_simulator.text = self.text
            self.text_simulator.simulate_typing()
        except Exception as e:
            logging.error(e)
            sys.exit(1)
