# src/parser.py
import argparse

class TypeSimulatorParser(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(description="Simulate human-like typing in an editor.")
        self.add_argument(
            "-e",
            "--editor_script",
            help="Path to the editor opening script",
            default=None,
        )
        self.add_argument(
            "-f",
            "--file",
            help="Path to the text file to type",
            default=None,
        )
        self.add_argument(
            "-s",
            "--speed",
            help="Typing speed in seconds per character",
            type=float,
            default=0.15,
        )
        self.add_argument(
            "-v",
            "--variance",
            help="Typing speed variance",
            type=float,
            default=0.05,
        )
        self.add_argument(
            "-m",
            "--window-mode",
            choices=["gui", "headless"],
            default="gui",
            help="Whether to launch a real GUI editor or headless (for E2E tests)",
        )
        self.add_argument(
            "text",
            nargs="?",
            help="Text to type directly",
            default=None,
        )

    def parse(self):
        return self.parse_args()
