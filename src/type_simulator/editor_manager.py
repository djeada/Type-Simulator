# src/type_simulator/editor_manager.py
import subprocess
import time
from pathlib import Path
from typing import Optional


class EditorManager:
    def __init__(
        self,
        editor_script_path: Optional[str] = None,
        mode: str = "gui",  # "gui" or "headless"
    ):
        self.mode = mode
        self.editor_script_path = (
            Path(editor_script_path).resolve() if editor_script_path else None
        )

    def open_editor(self):
        if self.mode == "headless":
            # headless/mock window for E2E tests
            from .mock_window import create_headless_window

            create_headless_window()
            return

        # real GUI mode
        if not self.editor_script_path or not self.editor_script_path.exists():
            raise FileNotFoundError(
                f"Editor script '{self.editor_script_path}' does not exist."
            )
        subprocess.Popen([str(self.editor_script_path)])
        time.sleep(2)
