# src/type_simulator/type_simulator.py
import logging
import sys
from typing import Optional

import pyautogui

from src.type_simulator.editor_manager import EditorManager
from src.type_simulator.file_manager import FileManager
from src.type_simulator.text_typer import TextTyper

class TypeSimulator:
    def __init__(
        self,
        editor_script_path: Optional[str] = "vi",
        file_path: Optional[str] = None,
        text: Optional[str] = None,
        typing_speed: float = 0.05,
        typing_variance: float = 0.05,
    ):
        pyautogui.FAILSAFE = False

        # initialize managers
        self.editor_manager = EditorManager(editor_script_path)
        self.file_manager = FileManager(file_path)

        self.text = text
        self.text_simulator = TextTyper(text, typing_speed, typing_variance)

    def run(self):
        try:
            # 1) open the editor on the target file
            self.editor_manager.open_editor(self.file_manager.file_path)

            # 2) if no text was passed on CLI, load it from the file
            if not self.text:
                self.text = self.file_manager.load_text()

            # 3) simulate typing
            self.text_simulator.text = self.text
            self.text_simulator.simulate_typing()

        except Exception as e:
            logging.error(e)
            sys.exit(1)
