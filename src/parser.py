# src/parser.py
"""
Type-Simulator CLI parser.

Defines all command-line options, including a safe --version flag
that exits before any GUI imports are performed.
"""

import argparse

# bump this on every release
VERSION = "2.0.0"

# Available typing profiles
TYPING_PROFILES = ["human", "fast", "slow", "robotic", "hunt_and_peck"]


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
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Basic direct mode
  python -m src.main --mode direct --output demo.txt --input "Hello, World!"

  # Use a typing profile
  python -m src.main --mode direct --output demo.txt --input "Fast typing" --profile fast

  # Show statistics after completion
  python -m src.main --mode direct --output demo.txt --input "Test" --stats

  # Use repeat blocks in input
  python -m src.main --mode direct --output demo.txt --input "{REPEAT_3}Hello {/REPEAT}"

Available Profiles:
  human        - Natural typing with realistic variations
  fast         - Quick professional typing
  slow         - Careful, deliberate typing
  robotic      - Mechanical, consistent typing
  hunt_and_peck - Slow, searching for keys
            """,
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
            default=None,
            help="Typing speed, in seconds per character. Overrides profile setting.",
        )
        self.add_argument(
            "-v",
            "--variance",
            type=float,
            default=None,
            help="Random variation in typing speed. Overrides profile setting.",
        )

        # typing profile
        self.add_argument(
            "-p",
            "--profile",
            choices=TYPING_PROFILES,
            default=None,
            help=(
                "Use a preset typing profile. "
                "Profiles: human, fast, slow, robotic, hunt_and_peck. "
                "Speed and variance flags override profile settings."
            ),
        )

        # input text (single flag only)
        self.add_argument(
            "-i",
            "--input",
            help="Input text to be typed. If a valid file path, reads from file; otherwise, treats as literal text. Required unless input is piped via STDIN.",
            type=str,
            required=False,
            default=None,
        )

        # output file (only for direct mode)
        self.add_argument(
            "-o",
            "--output",
            help="Output file path (only used in direct mode). Optional. If not provided in direct mode, will raise an error.",
            required=False,
            default=None,
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

        # statistics flag
        self.add_argument(
            "--stats",
            action="store_true",
            help="Show statistics after completion (characters typed, time taken, WPM).",
            default=False,
        )

        # list profiles
        self.add_argument(
            "--list-profiles",
            action="store_true",
            help="List all available typing profiles and exit.",
            default=False,
        )

    def parse(self):
        """Parse and return command-line arguments."""
        return self.parse_args()
