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
    FOCUS = "focus"  # New mode for focus typing


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
        pre_launch_cmd: Optional[str] = None,
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
            "Initialized with file_path=%s, mode=%s, wait=%s, editor_cmd=%s",
            file_path,
            mode,
            wait,
            editor_cmd,
        )

        # Detect focus mode: if file_path is None, switch to FOCUS
        if not file_path:
            self.mode = Mode.FOCUS
        else:
            self.mode = Mode(mode) if isinstance(mode, str) else mode
        self.wait = wait
        self.file_manager = FileManager(str(file_path)) if file_path else None
        self.text = text
        self.texter = TextTyper(text, typing_speed, typing_variance)
        self.pre_launch_cmd = pre_launch_cmd
        if self.mode in (Mode.GUI, Mode.TERMINAL):
            # Always honor explicit editor_cmd if provided
            if editor_cmd:
                cmd = editor_cmd
            else:
                cmd = (
                    "xterm -fa 'Monospace' -fs 10 -e vi"
                    if self.mode == Mode.GUI
                    else "xterm -e bash"
                )
            self.editor_manager = EditorManager(cmd)
        else:
            self.editor_manager = None

    def _execute_pre_launch_cmd(self) -> None:
        """Execute the pre-launch command if one is specified."""
        if not self.pre_launch_cmd:
            return

        self.logger.info(f"Running pre-launch command: {self.pre_launch_cmd}")
        try:
            import subprocess

            subprocess.run(self.pre_launch_cmd, shell=True, check=True)
        except Exception as e:
            self.logger.error(f"Pre-launch command failed: {e}")
            raise RuntimeError(f"Pre-launch command failed: {e}")

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
            except Exception:
                self.logger.exception("Editor mode failed")
                raise RuntimeError("Failed to run editor mode") from None

        self.logger.info("TypeSimulator completed successfully")

    def _run_direct(self) -> None:
        data = self.text or self.file_manager.load_text()
        self.file_manager.save_text(data)
        self.logger.info(
            "Direct mode: wrote %d characters to %s",
            len(data),
            self.file_manager.file_path,
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
        # wait before closing editor
        if self.wait and self.wait > 0:
            self.logger.debug("Waiting %s seconds before closing editor", self.wait)
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
                self.logger.debug(
                    "No automatic closing sequence for this editor; leaving open."
                )

        # Calculate a dynamic timeout based on text length and typing speed
        min_timeout = 10
        max_timeout = 120
        text_length = len(self.text) if self.text else 0
        word_count = len(self.text.split()) if self.text else 0
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
        Send keystrokes to the currently focused window using platform-specific tools:
        - Linux: xdotool
        - macOS: osascript (System Events)
        - Windows: pyautogui (direct)
        """
        self.logger.info("Focus mode: typing into the currently focused window.")

        # Validate required text input
        if not self.text:
            raise ValueError("No text provided for focus mode.")

        # Import dependencies
        import platform
        import shlex
        import subprocess
        from utils.utils import (
            is_program_installed,
            get_focus_mode_dependency,
            install_instructions,
        )

        # Get platform-specific dependency
        system = platform.system()
        required_tool = get_focus_mode_dependency(system)

        # Check dependencies if needed
        if required_tool and not is_program_installed(required_tool):
            raise RuntimeError(
                f"Required tool '{required_tool}' for focus mode on {system} "
                f"is not installed. {install_instructions(required_tool)}"
            )

        try:
            if system == "Linux":
                # Use xdotool with configured typing speed
                delay_ms = int(self.texter.typing_speed * 1000)
                cmd = ["xdotool", "type", "--delay", str(delay_ms)]

                # Handle special characters and line breaks
                lines = self.text.split("\\n")
                for i, line in enumerate(lines):
                    if i > 0:
                        subprocess.run(["xdotool", "key", "Return"], check=True)
                    if line:  # Skip empty lines
                        subprocess.run(cmd + [line], check=True)

            elif system == "Darwin":
                # Use AppleScript's System Events
                script = (
                    'tell application "System Events"\n'
                    f"delay {self.texter.typing_speed}\n"  # Initial delay
                    f"keystroke {shlex.quote(self.text)}\n"
                    "end tell"
                )
                subprocess.run(["osascript", "-e", script], check=True)

            elif system == "Windows":
                # Use PyAutoGUI directly
                import pyautogui

                pyautogui.write(self.text, interval=self.texter.typing_speed)

            else:
                raise NotImplementedError(f"Focus mode not supported on {system}")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Focus mode typing failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error in focus mode: {e}") from e

        self.logger.info("Focus mode typing completed successfully.")
