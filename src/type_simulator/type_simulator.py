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

        closing_done = False
        if self.mode == Mode.GUI and self.editor_manager:
            # Try to detect the editor and send the right closing sequence
            editor_cmd = self.editor_manager.editor_cmd.lower()
            self.logger.debug(f"Attempting to close editor: {editor_cmd}")
            if any(e in editor_cmd for e in ["vim", "vi"]):
                self.logger.debug("Saving and quitting vim/vi")
                pyautogui.press("esc")
                pyautogui.typewrite(":wq\n", interval=0.02)
                closing_done = True
            elif "nano" in editor_cmd:
                self.logger.debug("Saving and quitting nano")
                pyautogui.hotkey("ctrl", "x")
                time.sleep(0.2)
                pyautogui.press("y")
                time.sleep(0.1)
                pyautogui.press("enter")
                closing_done = True
            # Add more editors here as needed
            # For unknown editors, do not attempt to close automatically
            if not closing_done:
                self.logger.debug("No automatic closing sequence for this editor; leaving open.")

        # Calculate a dynamic timeout based on text length and typing speed
        min_timeout = 10
        max_timeout = 120
        text_length = len(self.text) if self.text else 0
        word_count = len(self.text.split()) if self.text else 0
        # Estimate: each character takes typing_speed + variance/2 on average
        avg_char_time = getattr(self.texter, 'typing_speed', 0.15) + getattr(self.texter, 'typing_variance', 0.05) / 2
        estimated_typing_time = text_length * avg_char_time
        # Add a buffer for editor startup/closing
        buffer_time = 5
        timeout = min(max(int(estimated_typing_time + buffer_time), min_timeout), max_timeout)
        self.logger.debug(f"Waiting for editor to exit (timeout={timeout}s, text_length={text_length}, avg_char_time={avg_char_time:.3f})")
        try:
            proc.wait(timeout=timeout)
        except Exception as e:
            self.logger.warning(f"Editor did not exit in time: {e}")
        self.logger.debug(
            "Editor exited with code %s", proc.returncode
        )
        # post-exit pause for stability (retain small delay)
        time.sleep(0.5)
