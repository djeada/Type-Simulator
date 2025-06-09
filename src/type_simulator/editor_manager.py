# src/type_simulator/editor_manager.py

import subprocess
import time
from typing import Optional

class EditorManager:
    def __init__(self, editor_cmd: Optional[str] = None):
        # editor_cmd can be a bare command (e.g. "vi") or a path to a script
        self.editor_cmd = editor_cmd or "vi"

    def open_editor(self, file_path: str):
        """
        Launches the editor command on the given file.
        e.g. ["vi", "/tmp/test.txt"] or ["./my_editor.sh", "/tmp/test.txt"]
        """
        cmd = [self.editor_cmd, file_path]
        subprocess.Popen(cmd)
        # give the editor a moment to start up before typing begins
        time.sleep(2)
