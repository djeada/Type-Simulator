# src/type_simulator/type_simulator.py
import logging
import sys
import time
import subprocess  # for process handles
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import pyautogui

from src.type_simulator.editor_manager import EditorManager
from src.type_simulator.file_manager import FileManager
from src.type_simulator.text_typer import TextTyper


class Mode(Enum):
    GUI = "gui"
    TERMINAL = "terminal"
    DIRECT = "direct"


class TypeSimulator:
    """
    Orchestrates typing text into a destination using three modes:

    - GUI:     open a GUI editor (default 'xterm -e vi') and drive it via PyAutoGUI
    - TERMINAL: open a terminal emulator for arbitrary shell commands
    - DIRECT:  write text directly to the file without GUI

    Backwards-compatible signature supports:
      TypeSimulator(editor_script_path, file_path, text, speed, variance)
    or the new:
      TypeSimulator(file_path, text, mode, editor_cmd, speed, variance).
    """

    def __init__(
        self,
        *args,
        mode: Mode = Mode.GUI,
        editor_cmd: Optional[str] = None,
        typing_speed: float = 0.05,
        typing_variance: float = 0.05,
        **kwargs,
    ):
        # Determine editor_script_path and file_path from args or kwargs
        if args and isinstance(args[0], str) and 'editor_script_path' in kwargs:
            # Old signature: (editor_script_path, file_path, text, speed, variance)
            editor_script_path = args[0]
            file_path = kwargs.get('file_path') or (args[1] if len(args) > 1 else None)
            text = kwargs.get('text') or (args[2] if len(args) > 2 else None)
            mode = kwargs.get('mode', mode)
            editor_cmd = editor_script_path
        else:
            # New signature: first positional is file_path
            file_path = args[0] if args else kwargs.get('file_path')
            text = args[1] if len(args) > 1 else kwargs.get('text')

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initialized with file_path=%s, mode=%s", file_path, mode)

        self.mode = mode
        self.file_manager = FileManager(str(file_path))
        self.text = text
        self.texter = TextTyper(text, typing_speed, typing_variance)

        if mode in (Mode.GUI, Mode.TERMINAL):
            cmd = editor_cmd or (
                "xterm -fa 'Monospace' -fs 10 -e vi" if mode == Mode.GUI else "xterm -e bash"
            )
            self.editor_manager = EditorManager(cmd)
        else:
            self.editor_manager = None

    def run(self) -> None:
        """Execute the typing workflow based on the selected mode."""
        self.logger.info("Starting TypeSimulator in %s mode", self.mode.value)
        try:
            if self.mode == Mode.DIRECT:
                self._run_direct()
            else:
                proc = self._launch_editor()
                self._type_content()
                self._finalize(proc)
        except Exception:
            self.logger.exception("TypeSimulator failed")
            sys.exit(1)
        self.logger.info("TypeSimulator completed successfully")

    def _run_direct(self) -> None:
        data = self.text or self.file_manager.load_text()
        self.file_manager.save_text(data)
        self.logger.info(
            "Direct mode: wrote %d characters to %s",
            len(data), self.file_manager.file_path
        )

    def _launch_editor(self) -> subprocess.Popen:
        path = self.file_manager.file_path
        self.logger.debug("Launching editor for file: %s", path)
        proc = self.editor_manager.open_editor(path)
        self.logger.debug("Editor launched, PID=%s", proc.pid)
        return proc

    def _type_content(self) -> None:
        if not self.text:
            self.text = self.file_manager.load_text()
            self.logger.debug(
                "Loaded text from file: %d characters", len(self.text)
            )
        else:
            self.logger.debug(
                "Using provided text: %d characters", len(self.text)
            )

        if self.mode == Mode.GUI:
            self.logger.debug("Entering insert mode")
            pyautogui.press("i")
            time.sleep(0.1)

        self.logger.info("Simulating typing of %d characters", len(self.text))
        self.texter.text = self.text
        self.texter.simulate_typing()

    def _finalize(self, proc: subprocess.Popen) -> None:
        if self.mode == Mode.GUI:
            self.logger.debug("Saving and quitting editor")
            pyautogui.press("esc")
            pyautogui.typewrite(":wq\n", interval=0.02)
        self.logger.debug("Waiting for editor to exit")
        proc.wait(timeout=10)
        self.logger.debug(
            "Editor exited with code %s", proc.returncode
        )
        time.sleep(0.5)
