#!/usr/bin/env python3
# src/type_simulator/type_simulator.py
import logging
import sys
import time
import subprocess  # for process handles
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import pyautogui

from type_simulator.editor_manager import EditorManager
from type_simulator.file_manager import FileManager
from type_simulator.text_typer import TextTyper


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
      TypeSimulator(file_path, text, mode, editor_cmd, speed, variance, wait)
    """

    def __init__(
        self,
        *args,
        mode: Mode = Mode.GUI,
        editor_cmd: Optional[str] = None,
        typing_speed: float = 0.05,
        typing_variance: float = 0.05,
        wait: float = 0.0,
        **kwargs,
    ):
        # Unpack arguments for backward and forward compatibility
        # Priority: explicit keyword > positional > None
        file_path = None
        text = None
        # Handle legacy signature: (editor_script_path, file_path, text, ...)
        if args:
            if len(args) == 3:
                # (editor_script_path, file_path, text)
                editor_script_path, file_path, text = args
                if not editor_cmd:
                    editor_cmd = editor_script_path
            elif len(args) == 2:
                # (file_path, text)
                file_path, text = args
            elif len(args) == 1:
                file_path = args[0]
        # Allow keyword overrides
        file_path = kwargs.get('file_path', file_path)
        text = kwargs.get('text', text)
        if 'editor_script_path' in kwargs and not editor_cmd:
            editor_cmd = kwargs['editor_script_path']
        if 'editor_cmd' in kwargs and not editor_cmd:
            editor_cmd = kwargs['editor_cmd']

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(
            "Initialized with file_path=%s, mode=%s, wait=%s, editor_cmd=%s",
            file_path, mode, wait, editor_cmd
        )

        self.mode = mode
        self.wait = wait
        self.file_manager = FileManager(str(file_path))
        self.text = text
        self.texter = TextTyper(text, typing_speed, typing_variance)

        if mode in (Mode.GUI, Mode.TERMINAL):
            # Always honor explicit editor_cmd if provided
            if editor_cmd:
                cmd = editor_cmd
            else:
                cmd = (
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
        # wait before closing editor
        if self.wait and self.wait > 0:
            self.logger.debug(
                "Waiting %s seconds before closing editor", self.wait
            )
            time.sleep(self.wait)

        if self.mode == Mode.GUI:
            self.logger.debug("Saving and quitting editor")
            pyautogui.press("esc")
            pyautogui.typewrite(":wq\n", interval=0.02)
        self.logger.debug("Waiting for editor to exit")
        proc.wait(timeout=10)
        self.logger.debug(
            "Editor exited with code %s", proc.returncode
        )
        # post-exit pause for stability (retain small delay)
        time.sleep(0.5)
