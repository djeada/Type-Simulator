#!/usr/bin/env python3
# src/type_simulator/type_simulator.py
"""
Type-Simulator core module.

This module provides the main TypeSimulator class that orchestrates
typing text into various destinations using different modes.
"""

import logging
import os
import shlex
import time
import subprocess  # for process handles
from enum import Enum
from typing import Optional

from type_simulator.editor_manager import EditorManager
from type_simulator.file_manager import FileManager
from type_simulator.text_typer.__main__ import TextTyper


def _get_pyautogui():
    """Lazily import pyautogui only when needed for GUI operations."""
    import pyautogui

    return pyautogui


class Mode(Enum):
    """Typing mode enumeration."""

    GUI = "gui"
    TERMINAL = "terminal"
    DIRECT = "direct"
    FOCUS = "focus"
    REEL = "reel"


VI_EDITORS = {"vi", "vim", "nvim", "gvim", "view"}


class TypeSimulator:
    """
    Orchestrates typing text into a destination using four modes:

    - GUI:     open a GUI editor (default 'xterm -e vi') and drive it via PyAutoGUI
    - TERMINAL: open a terminal emulator for arbitrary shell commands
    - DIRECT:  expand macros and write the result directly to the file, no GUI
    - FOCUS:   type into the currently focused window

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
        typing_speed: float = 0.15,
        typing_variance: float = 0.05,
        wait: float = 0.0,
        pre_launch_cmd: Optional[str] = None,
        geometry: Optional[str] = None,
        pause_probability: float = 0.0,
        pause_duration: float = 0.0,
        resolve_text: bool = True,
        **kwargs,
    ):
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
        file_path = kwargs.get("file_path", file_path)
        text = kwargs.get("text", text)
        if "editor_script_path" in kwargs and not editor_cmd:
            editor_cmd = kwargs["editor_script_path"]
        if "editor_cmd" in kwargs and not editor_cmd:
            editor_cmd = kwargs["editor_cmd"]

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(
            "Initialized with file_path=%s, mode=%s, wait=%s, editor_cmd=%s, geometry=%s",
            file_path,
            mode,
            wait,
            editor_cmd,
            geometry,
        )

        # Resolve text that may be a file path or come from stdin, unless the
        # caller already did (resolving twice would treat content as a path)
        if text is not None and resolve_text:
            try:
                from utils.text_input import get_text_content

                text = get_text_content(text)
            except Exception as e:
                self.logger.debug(f"Error processing text input: {e}")

        # Respect the requested mode; only infer focus when mode is unset.
        if mode is None:
            self.mode = Mode.FOCUS if not file_path else Mode.GUI
        else:
            self.mode = Mode(mode) if isinstance(mode, str) else mode
        self.wait = wait
        self.file_manager = FileManager(str(file_path)) if file_path else None
        self.text = text
        self.pre_launch_cmd = pre_launch_cmd
        self.rendered_text: Optional[str] = None
        if self.mode == Mode.REEL:
            raise ValueError(
                "Reel mode renders a video; use type_simulator.reel.render_reel()"
            )
        if self.mode == Mode.DIRECT and not self.file_manager:
            raise ValueError("Direct mode requires a file path.")

        # Check for terminal availability early (before TextTyper init)
        # so users get a helpful error message about missing terminals
        if self.mode in (Mode.GUI, Mode.TERMINAL):
            # Always honor explicit editor_cmd if provided
            if editor_cmd:
                cmd = editor_cmd
            else:
                if self.mode == Mode.GUI:
                    cmd = "xterm -fa 'Monospace' -fs 10 -e vi"
                else:
                    # Terminal mode: detect available terminal emulator
                    from utils.utils import get_default_terminal_command

                    cmd, error = get_default_terminal_command(geometry=geometry)
                    if cmd is None:
                        raise RuntimeError(error)
            self.editor_manager = EditorManager(cmd)
        else:
            self.editor_manager = None

        # The GUI backend is only initialized when typing starts, so building
        # a simulator (e.g. for --dry-run or direct mode) needs no display.
        self.texter = TextTyper(
            text,
            typing_speed,
            typing_variance,
            lazy_init=True,
            pause_probability=pause_probability,
            pause_duration=pause_duration,
        )

    def _execute_pre_launch_cmd(self) -> None:
        """Execute the pre-launch command if one is specified."""
        if not self.pre_launch_cmd:
            return

        self.logger.info(f"Running pre-launch command: {self.pre_launch_cmd}")
        try:
            subprocess.run(self.pre_launch_cmd, shell=True, check=True)
        except Exception as e:
            self.logger.error(f"Pre-launch command failed: {e}")
            raise RuntimeError(f"Pre-launch command failed: {e}") from e

    def run(self) -> None:
        """Execute the typing workflow based on the selected mode."""
        self.logger.info("Starting TypeSimulator in %s mode", self.mode.value)

        # Let expected errors propagate up
        self._execute_pre_launch_cmd()

        if self.mode == Mode.DIRECT:
            self._run_direct()
        elif self.mode == Mode.FOCUS:
            self._run_focus()
        else:
            try:
                proc = self._launch_editor()
                self._type_content()
                self._finalize(proc)
            except Exception as e:
                self.logger.exception("Editor mode failed")
                raise RuntimeError(f"Failed to run editor mode: {e}") from e

        self.logger.info("TypeSimulator completed successfully")

    def _run_direct(self) -> None:
        source = self.text if self.text is not None else self.file_manager.load_text()
        self.texter.text = source
        data = self.texter.render()
        self.rendered_text = data
        self.file_manager.save_text(data)
        self.logger.info(
            "Direct mode: wrote %d characters to %s",
            len(data),
            self.file_manager.file_path,
        )

    def _launch_editor(self) -> subprocess.Popen:
        path = self.file_manager.file_path if self.file_manager else None
        if path:
            self.logger.debug("Launching editor for file: %s", path)
        else:
            self.logger.debug("Launching editor without a file target")
        proc = self.editor_manager.open_editor(path)
        self.logger.debug("Editor launched, PID=%s", proc.pid)
        return proc

    def _type_content(self) -> None:
        if not self.text:
            self.text = self.file_manager.load_text()
            self.logger.debug("Loaded text from file: %d characters", len(self.text))
        else:
            self.logger.debug("Using provided text: %d characters", len(self.text))

        if self.mode == Mode.GUI:
            self.logger.debug("Entering insert mode")
            pyautogui = _get_pyautogui()
            pyautogui.press("i")
            time.sleep(0.1)

        self.logger.info("Simulating typing of %d characters", len(self.text))
        self.texter.text = self.text
        self.texter.simulate_typing()

    def _finalize(self, proc: subprocess.Popen) -> None:
        # wait before closing editor
        if self.wait and self.wait > 0:
            self.logger.debug("Waiting %s seconds before closing editor", self.wait)
            time.sleep(self.wait)

        closing_done = False
        if self.mode == Mode.GUI and self.editor_manager:
            pyautogui = _get_pyautogui()
            # Try to detect the editor and send the right closing sequence
            editor_cmd = self.editor_manager.editor_cmd.lower()
            self.logger.debug(f"Attempting to close editor: {editor_cmd}")
            programs = {os.path.basename(part) for part in shlex.split(editor_cmd)}
            if programs & VI_EDITORS:
                self.logger.debug("Saving and quitting vim/vi")
                pyautogui.press("esc")
                pyautogui.typewrite(":wq\n", interval=0.02)
                closing_done = True
            elif "nano" in programs:
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
                self.logger.debug(
                    "No automatic closing sequence for this editor; leaving open."
                )

        # Calculate a dynamic timeout based on text length and typing speed
        min_timeout = 10
        max_timeout = 120
        text_length = len(self.text) if self.text else 0
        # Estimate: each character takes typing_speed + variance/2 on average
        avg_char_time = (
            getattr(self.texter, "typing_speed", 0.15)
            + getattr(self.texter, "typing_variance", 0.05) / 2
        )
        estimated_typing_time = text_length * avg_char_time
        # Add a buffer for editor startup/closing
        buffer_time = 5
        timeout = min(
            max(int(estimated_typing_time + buffer_time), min_timeout), max_timeout
        )
        self.logger.debug(
            f"Waiting for editor to exit (timeout={timeout}s, text_length={text_length}, avg_char_time={avg_char_time:.3f})"
        )
        try:
            proc.wait(timeout=timeout)
        except Exception as e:
            self.logger.warning(f"Editor did not exit in time: {e}")
        self.logger.debug("Editor exited with code %s", proc.returncode)
        # post-exit pause for stability (retain small delay)
        time.sleep(0.5)

    def _run_focus(self) -> None:
        """
        Focus mode: simulate all text, key sequences, and waits in the current window.
        Delegates to TextTyper to honor {…} commands.
        """
        self.logger.info("Focus mode: typing into the currently focused window.")

        if not self.text:
            raise ValueError("No text provided for focus mode.")

        # Delegate parsing and execution to TextTyper
        self.logger.debug("Delegating to TextTyper for focus-mode typing")
        self.texter.text = self.text
        self.texter.simulate_typing()

        self.logger.info("Focus mode typing completed successfully.")
