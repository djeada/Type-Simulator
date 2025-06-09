# src/type_simulator/type_simulator.py
import logging
import sys
import time
from typing import Optional

import pyautogui

from src.type_simulator.editor_manager import EditorManager
from src.type_simulator.file_manager import FileManager
from src.type_simulator.text_typer import TextTyper


class TypeSimulator:
    """
    High-level workflow:

      1. Launch xterm+Vim on the target file.
      2. Enter insert mode.
      3. Simulate human-like typing.
      4. Save (`:wq`) and wait for Vim to exit.
    """

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
        self.texter = TextTyper(text, typing_speed, typing_variance)

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        try:
            # 1. Launch the editor.
            proc = self.editor_manager.open_editor(self.file_manager.file_path)

            # 2. Decide what to type.
            if not self.text:
                self.text = self.file_manager.load_text()
            logging.debug("Typing %d characters.", len(self.text))

            # 3. Enter insert mode & type.
            pyautogui.press("i")
            time.sleep(0.1)

            self.texter.text = self.text
            self.texter.simulate_typing()

            # 4. Save & quit, then wait for Vim to exit so file is flushed.
            logging.info("Typing complete – saving & quitting Vim…")
            pyautogui.press("esc")
            pyautogui.typewrite(":wq\n", interval=0.02)

            proc.wait(timeout=5)
            logging.info("Editor exited cleanly.")
            time.sleep(0.4)

        except Exception as exc:  # noqa: BLE001
            logging.error("Type simulation failed: %s", exc, exc_info=True)
            sys.exit(1)
