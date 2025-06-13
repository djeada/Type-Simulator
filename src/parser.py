# src/parser.py
"""
Type-Simulator CLI parser.

Defines all command-line options, including a safe --version flag
that exits before any GUI imports are performed.
"""

import argparse

# bump this on every release
VERSION = "1.0.0"


class TypeSimulatorParser(argparse.ArgumentParser):
    """
    Command-line interface for Type-Simulator.

    If --editor-script is omitted, the simulator will
    default to launching 'xterm -e vi', guaranteeing
    a real TTY even under Xvfb.
    """

    def __init__(self) -> None:
        super().__init__(
            prog="type_simulator",
            description="Simulate human-like typing in an editor or window.",
        )

        # editorlauncher
        self.add_argument(
            "-e",
            "--editor-script",
            help=(
                "Command used to open the editor "
                "(e.g. 'xterm -e vi' or 'gedit'). "
                "If omitted, defaults to 'xterm -e vi'."
            ),
            default=None,
        )

        # input file (optional in focus mode)
        self.add_argument(
            "-f",
            "--file",
            help=(
                "Path to the text file to type into. "
                "If omitted, focus mode is enabled."
            ),
            required=False,
        )

        # typing mode
        self.add_argument(
            "--mode",
            choices=["gui", "terminal", "direct", "focus"],
            default="gui",
            help=(
                "Typing mode: "
                "gui (editor), terminal (shell), direct (file), "
                "or focus (active window)."
            ),
        )

        # speed parameters
        self.add_argument(
            "-s",
            "--speed",
            type=float,
            default=0.15,
            help="Typing speed, in seconds per character.",
        )
        self.add_argument(
            "-v",
            "--variance",
            type=float,
            default=0.05,
            help="Random variation in typing speed.",
        )

        # direct text input (optional in focus mode)
        self.add_argument(
            "-t",
            "--text",
            help=(
                "Text to type directly. "
                "If omitted, will read from --file if provided."
            ),
            required=False,
        )

        # logging verbosity
        self.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Logging verbosity (default: INFO).",
        )

        # post-type delay
        self.add_argument(
            "-w",
            "--wait",
            type=float,
            default=0.0,
            help=(
                "Seconds to wait after typing completes "
                "before closing the editor (default: 0)."
            ),
        )

        # hook to run before launch
        self.add_argument(
            "--pre-launch-cmd",
            help=(
                "Run this command synchronously before launching the "
                "editor or typing (e.g. start a recorder)."
            ),
            default=None,
        )

        # version flag (exits immediately, no GUI imports)
        self.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"%(prog)s {VERSION}",
            help="Show program’s version number and exit.",
        )

        # dry run mode
        self.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate input without executing actions. Useful for checking if commands are parsable.",
            default=False,
        )

        # input text
        text_group = self.add_mutually_exclusive_group(required=True)
        text_group.add_argument(
            "-i",
            "--input",
            help="Input text to be typed (overrides file).",
            type=str,
            default=None,
        )
        text_group.add_argument(
            "-F",
            "--file-input",
            help="File to read input text from (overrides --input).",
            type=argparse.FileType("r"),
            default=None,
        )

    def parse(self):
        """Parse and return command-line arguments."""
        return self.parse_args()
