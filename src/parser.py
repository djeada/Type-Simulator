# src/parser.py
import argparse


class TypeSimulatorParser(argparse.ArgumentParser):
    """
    CLI for Type-Simulator.
    ──────────────────────
    If --editor-script is **omitted**, we fall back to the EditorManager
    default ("xterm -e vi"), which guarantees Vim has a real TTY even
    under Xvfb.
    """

    def __init__(self):
        super().__init__(description="Simulate human-like typing in an editor.")
        self.add_argument(
            "-e",
            "--editor-script",
            help="Command used to open the editor "
            "(e.g. 'xterm -e vi' or 'gedit'). "
            "If omitted, defaults to 'xterm -e vi'.",
            default=None,  # ← key change: let EditorManager decide
        )
        self.add_argument(
            "-f",
            "--file",
            required=True,
            help="Path to the text file to type into",
        )
        self.add_argument(
            "-s",
            "--speed",
            type=float,
            default=0.15,
            help="Typing speed (seconds per character)",
        )
        self.add_argument(
            "-v",
            "--variance",
            type=float,
            default=0.05,
            help="Random typing speed variance",
        )
        self.add_argument(
            "-t",
            "--text",
            required=True,
            help="Text to type",
        )
        self.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Verbosity of logs (default INFO)",
        )
        self.add_argument(
            "-w", "--wait",
            type=float,
            default=0.0,
            help=(
                "Seconds to wait after typing is done "
                "and before closing the editor (default: 0)"
            ),
        )
        self.add_argument(
            "--pre-launch-cmd",
            help="Command to run synchronously before launching the editor or typing (e.g. open a terminal, start a recorder)",
            default=None,
        )

    def parse(self):
        return self.parse_args()
