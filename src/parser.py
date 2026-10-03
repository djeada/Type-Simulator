# src/parser.py
"""
Type-Simulator CLI parser.

Defines all command-line options, including a safe --version flag
that exits before any GUI imports are performed.
"""

import argparse

# bump this on every release
VERSION = "2.2.0"

# Available typing profiles
TYPING_PROFILES = [
    "human",
    "fast",
    "slow",
    "robotic",
    "hunt_and_peck",
    "programmer",
    "storyteller",
    "casual",
    "expert",
    "nervous",
]

# Kept in sync with type_simulator.reel.themes.THEMES (checked by a unit test);
# importing it here would pull in Pillow before --version/--help.
REEL_THEMES = ["hacker", "dracula", "monokai", "nord"]


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
            description="🎹 Type-Simulator - Simulate human-like typing in any editor or window.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Basic direct mode - write to file
  python -m src.main --mode direct --output demo.txt --input "Hello, World!"

  # Use a typing profile for natural typing
  python -m src.main --mode direct --output demo.txt --input "Fast typing" --profile fast

  # Show statistics after completion
  python -m src.main --mode direct --output demo.txt --input "Test" --stats

  # Macros are expanded in direct mode too
  python -m src.main --mode direct --output demo.txt --input "{REPEAT_3}Hello {/REPEAT}"

  # Use macros for complex automation
  python -m src.main --mode focus --input "{SET_name=World}Hello, {GET_name}!"

  # Render a vertical reel/short: type a script in vim, run it, with music
  python -m src.main --mode reel --input hack.py --output reel.mp4 \
      --title "Hacking the mainframe" --footer "@me" --duration 30

Available Profiles:
  human         - Natural typing with realistic variations (0.08s, ±0.04)
  fast          - Quick professional typing (0.03s, ±0.01)
  slow          - Careful, deliberate typing (0.2s, ±0.08)
  robotic       - Mechanical, consistent typing (0.05s, no variance)
  hunt_and_peck - Slow, searching for keys (0.4s, ±0.2)
  programmer    - Fast with thinking pauses (0.05s, ±0.03)
  storyteller   - Dramatic pauses for effect (0.1s, ±0.05)
  casual        - Relaxed, informal rhythm (0.12s, ±0.08)
  expert        - Ultra-fast touch typist (0.02s, ±0.005)
  nervous       - Quick bursts with hesitations (0.06s, ±0.04)

Macro Commands:
  {REPEAT_N}...{/REPEAT}  - Repeat text N times
  {RANDOM_N}              - Generate N random characters
  {WAIT_N}                - Wait N seconds
  {SPEED_N}               - Change typing speed to N seconds
  {SET_var=value}         - Set a variable
  {GET_var}               - Get a variable value
  {LOOP_N_var}...{/LOOP}  - Loop N times, {GET_var} gives the 1-based index
  {COUNTER[_name][_init|next|get][_start]} - Sequential numbering
  {DATE} {TIME} {DATETIME_fmt} - Current date/time (strftime format)
  {NL_N} {TAB_N}          - Insert N newlines / tabs
  {<key>}                 - Press a key (enter, esc, tab, etc.)
  {<ctrl>+<key>}          - Key combination
  {MOUSE_MOVE_X_Y} {MOUSE_CLICK_btn} - Mouse actions (ignored in direct mode)

For more information, visit: https://github.com/djeada/Type-Simulator
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
            choices=["gui", "terminal", "direct", "focus", "reel"],
            default="gui",
            help=(
                "Typing mode: "
                "gui (editor), terminal (shell), direct (file), "
                "focus (active window), or reel (render a video)."
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
                "Use a preset typing profile (see --list-profiles). "
                "Speed and variance flags override profile settings."
            ),
        )

        # input text (single flag only)
        self.add_argument(
            "-i",
            "--input",
            help=(
                "Input text to be typed. If a valid file path, reads from file; "
                "otherwise, treats as literal text. Required unless input is piped via STDIN."
            ),
            type=str,
            required=False,
            default=None,
        )

        # output file (only for direct mode)
        self.add_argument(
            "-o",
            "--output",
            help=(
                "Output file path (required in direct and reel modes, "
                "ignored otherwise)."
            ),
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

        # check terminal availability
        self.add_argument(
            "--check-terminals",
            action="store_true",
            help="Check and display available terminal emulators on this system.",
            default=False,
        )

        # geometry for terminal mode
        self.add_argument(
            "-g",
            "--geometry",
            help=(
                "Terminal window geometry (only used in terminal mode). "
                "Format: WIDTHxHEIGHT (e.g., '80x24' for 80 columns by 24 rows)."
            ),
            type=str,
            default=None,
        )

        self._add_reel_arguments()

    def _add_reel_arguments(self) -> None:
        reel = self.add_argument_group(
            "reel mode",
            "Render a vertical video (Reels/Shorts/TikTok) of the --input script "
            "being typed into vim, saved and executed. Requires ffmpeg.",
        )
        reel.add_argument("--title", help="Headline above the terminal.")
        reel.add_argument("--subtitle", help="Smaller line under the title.")
        reel.add_argument("--footer", help="Text under the terminal, e.g. '@handle'.")
        reel.add_argument(
            "--theme", choices=REEL_THEMES, default="hacker", help="Color theme."
        )
        reel.add_argument(
            "--prompt", help="Shell prompt user@host (default depends on theme)."
        )
        reel.add_argument(
            "--filename", help="File name shown on screen (default: input file name)."
        )
        reel.add_argument(
            "--duration",
            type=float,
            help="Scale typing speed so the reel lasts about this many seconds.",
        )
        reel.add_argument(
            "--music",
            default="builtin",
            help=(
                "Background music: 'builtin' (generated, royalty-free), "
                "an audio file path, or 'none'."
            ),
        )
        reel.add_argument("--music-volume", type=float, default=0.35)
        reel.add_argument("--key-volume", type=float, default=0.6)
        reel.add_argument(
            "--no-key-sounds", action="store_true", help="Disable keyboard clicks."
        )
        reel.add_argument(
            "--run-cmd",
            help="Command typed to run the script; {file} is the file name "
            "(default: by extension or shebang, e.g. 'python3 {file}').",
        )
        reel.add_argument(
            "--no-run", action="store_true", help="Only type the script, don't run it."
        )
        reel.add_argument(
            "--fake-output",
            metavar="FILE",
            help="Show this file's contents as the program output instead of "
            "running the script (ANSI colors supported).",
        )
        reel.add_argument(
            "--run-timeout",
            type=float,
            default=20.0,
            help="Stop the script after this many seconds (default: 20).",
        )
        reel.add_argument(
            "--size",
            default="1080x1920",
            help="Video size WIDTHxHEIGHT (default: 1080x1920).",
        )
        reel.add_argument("--fps", type=int, default=30)
        reel.add_argument("--font", help="Path to a monospace .ttf font.")
        reel.add_argument("--font-size", type=int, help="Terminal font size in px.")
        reel.add_argument(
            "--seed", type=int, help="Random seed for reproducible typing and music."
        )
        reel.add_argument(
            "--preview",
            action="store_true",
            help="Write a single PNG frame to --output instead of a video.",
        )

    def parse(self):
        """Parse and return command-line arguments."""
        return self.parse_args()
