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
    def open_editor(self, file_path: Optional[str] = None) -> subprocess.Popen:
        cmd = shlex.split(self.editor_cmd)
        window_class = os.path.basename(cmd[0]) if cmd else None
        window_name = None
        if file_path:
            cmd.append(str(file_path))
            window_name = os.path.basename(str(file_path))

        logging.info("Launching editor: %s", " ".join(map(str, cmd)))

        proc = subprocess.Popen(cmd)
        time.sleep(2)  # allow the window to appear

        focused = self._focus_window_by_pid(proc.pid)
        if not focused and window_name:
            focused = self._focus_window(window_name)
        if not focused and window_class:
            self._focus_window_by_class(window_class)
        return proc

    # ------------------------------------------------------------------ #
    @staticmethod
    def _focus_window(window_name: str) -> bool:
        try:
            win_id = (
                subprocess.check_output(["xdotool", "search", "--name", window_name])
                .splitlines()[0]
                .decode()
            )
            subprocess.run(["xdotool", "windowactivate", "--sync", win_id])
            time.sleep(0.4)
            logging.debug("Focused window %s (id=%s)", window_name, win_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logging.debug("Could not focus window (%s)", exc)
            return False

    @staticmethod
    def _focus_window_by_pid(pid: int) -> bool:
        for _ in range(10):
            try:
                win_id = (
                    subprocess.check_output(["xdotool", "search", "--pid", str(pid)])
                    .splitlines()[0]
                    .decode()
                )
                subprocess.run(["xdotool", "windowactivate", "--sync", win_id])
                time.sleep(0.2)
                logging.debug("Focused window for pid=%s (id=%s)", pid, win_id)
                return True
            except Exception as exc:  # noqa: BLE001
                logging.debug("PID focus attempt failed (%s)", exc)
                time.sleep(0.2)
        return False

    @staticmethod
    def _focus_window_by_class(window_class: str) -> bool:
        try:
            win_id = (
                subprocess.check_output(["xdotool", "search", "--class", window_class])
                .splitlines()[-1]
                .decode()
            )
            subprocess.run(["xdotool", "windowactivate", "--sync", win_id])
            time.sleep(0.2)
            logging.debug("Focused window class=%s (id=%s)", window_class, win_id)
            return True
        except Exception as exc:  # noqa: BLE001
            logging.debug("Could not focus window class (%s)", exc)
            return False
