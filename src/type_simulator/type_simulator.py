# src/type_simulator/type_simulator.py
import logging
import sys
import time
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

    - GUI: launches a graphical editor (default 'xterm -e vi') and drives it via PyAutoGUI
    - TERMINAL: opens a terminal emulator for arbitrary shell commands
    - DIRECT: writes text directly to the file without GUI

    Attributes
    ----------
    mode : Mode
        The execution mode.
    file_manager : FileManager
        Manages file creation and I/O.
    editor_manager : Optional[EditorManager]
        Manages launching and focusing the editor (None in DIRECT mode).
    texter : TextTyper
        Simulates human-like typing.
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        text: Optional[str] = None,
        mode: Mode = Mode.GUI,
        editor_cmd: Optional[str] = None,
        typing_speed: float = 0.05,
        typing_variance: float = 0.05,
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mode = mode
        self.file_manager = FileManager(file_path)
        self.text = text
        self.texter = TextTyper(text, typing_speed, typing_variance)

        if mode in (Mode.GUI, Mode.TERMINAL):
            cmd = editor_cmd or ("xterm -fa 'Monospace' -fs 10 -e vi" if mode == Mode.GUI else "xterm -e bash")
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
        except Exception as exc:
            self.logger.exception("TypeSimulator failed")
            sys.exit(1)
        self.logger.info("TypeSimulator completed successfully")

    def _run_direct(self) -> None:
        """Directly write text to the file without GUI."""
        data = self.text or self.file_manager.load_text()
        self.file_manager.save_text(data)
        self.logger.info("Direct mode: wrote %d characters to %s", len(data), self.file_manager.file_path)

    def _launch_editor(self) -> subprocess.Popen:
        """Launch the editor and return the process handle."""
        path = self.file_manager.file_path
        self.logger.debug("Launching editor for file: %s", path)
        proc = self.editor_manager.open_editor(path)
        self.logger.debug("Editor launched, PID=%s", proc.pid)
        return proc

    def _type_content(self) -> None:
        """Enter insert mode (if GUI), then simulate typing."""
        if not self.text:
            self.text = self.file_manager.load_text()
            self.logger.debug("Loaded text from file: %d characters", len(self.text))
        else:
            self.logger.debug("Using provided text: %d characters", len(self.text))

        if self.mode == Mode.GUI:
            self.logger.debug("Entering insert mode")
            pyautogui.press("i")
            time.sleep(0.1)

        self.logger.info("Simulating typing of %d characters", len(self.text))
        self.texter.text = self.text
        self.texter.simulate_typing()

    def _finalize(self, proc: subprocess.Popen) -> None:
        """Save & quit (for GUI) or simply wait for process to exit."""
        if self.mode == Mode.GUI:
            self.logger.debug("Saving and quitting editor")
            pyautogui.press("esc")
            pyautogui.typewrite(":wq\n", interval=0.02)
        self.logger.debug("Waiting for editor to exit")
        proc.wait(timeout=10)
        self.logger.debug("Editor exited with code %s", proc.returncode)
        time.sleep(0.5)
