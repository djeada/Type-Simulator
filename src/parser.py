# src/parser.py
import argparse

class TypeSimulatorParser(argparse.ArgumentParser):
    def __init__(self):
        super().__init__(description="Simulate human-like typing in an editor.")
        self.add_argument(
            "-e", "--editor-script",
            help="Editor command or script (defaults to 'vi')",
            default="vi",
        )
        self.add_argument(
            "-f", "--file",
            help="Path to the text file to type",
            required=True,
        )
        self.add_argument(
            "-s", "--speed",
            help="Typing speed in seconds per character",
            type=float,
            default=0.15,
        )
        self.add_argument(
            "-v", "--variance",
            help="Typing speed variance",
            type=float,
            default=0.05,
        )
        self.add_argument(
            "-t", "--text",
            help="Text to type directly",
            required=True,
        )

    def parse(self):
        return self.parse_args()
