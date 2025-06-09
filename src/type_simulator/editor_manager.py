# src/type_simulator/editor_manager.py
import logging
import os
import shlex
import subprocess
import time
from typing import Optional


class EditorManager:
    """
    Launches the editor in an xterm window and focuses it (best-effort).
    """

    DEFAULT_CMD = 'xterm -fa "Monospace" -fs 10 -e vi'

    def __init__(self, editor_cmd: Optional[str] = None):
        self.editor_cmd = editor_cmd or self.DEFAULT_CMD

    # ------------------------------------------------------------------ #
    def open_editor(
        self, file_path
    ) -> subprocess.Popen:  # file_path can be Path or str
        # 👉 ensure file_path is str so subprocess + logging don't choke
        cmd = shlex.split(self.editor_cmd) + [str(file_path)]

        # stringify every element for neat logging
        logging.info("Launching editor: %s", " ".join(map(str, cmd)))

        proc = subprocess.Popen(cmd)
        time.sleep(2)  # allow the window to appear

        self._focus_window(os.path.basename(str(file_path)))
        return proc

    # ------------------------------------------------------------------ #
    @staticmethod
    def _focus_window(window_name: str) -> None:
        try:
            win_id = (
                subprocess.check_output(["xdotool", "search", "--name", window_name])
                .splitlines()[0]
                .decode()
            )
            subprocess.run(["xdotool", "windowactivate", "--sync", win_id])
            time.sleep(0.4)
            logging.debug("Focused window %s (id=%s)", window_name, win_id)
        except Exception as exc:  # noqa: BLE001
            logging.debug("Could not focus window (%s)", exc)
