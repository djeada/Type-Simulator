# src/type_simulator/editor_manager.py
import subprocess
import time
from typing import Optional

class EditorManager:
    def __init__(self, editor_script_path: Optional[str] = "vi"):
        # editor_script_path can be a command like 'vi' or a path to a script
        self.editor_cmd = editor_script_path or "vi"

    def open_editor(self, file_path: str):
        # Launch editor with the target file
        # e.g. ['vi', '/tmp/test.txt'] or ['./my_editor.sh', '/tmp/test.txt']
        cmd = [self.editor_cmd, file_path]
        subprocess.Popen(cmd)
        # give the editor a moment to spin up
        time.sleep(2)
