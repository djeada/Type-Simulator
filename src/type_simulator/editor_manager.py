import subprocess
import time
from pathlib import Path
from typing import Optional


class EditorManager:
    def __init__(self, editor_script_path: Optional[str] = None):
        self.editor_script_path = (
            Path(editor_script_path).resolve() if editor_script_path else None
        )

    def open_editor(self):
        if self.editor_script_path and not self.editor_script_path.exists():
            raise FileNotFoundError(
                f"Editor script '{self.editor_script_path}' does not exist."
            )
        if self.editor_script_path:
            subprocess.Popen([str(self.editor_script_path)])
            time.sleep(2)
