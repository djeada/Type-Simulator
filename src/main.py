# src/main.py
#!/usr/bin/env python3
import logging
import sys

from src.parser import TypeSimulatorParser
from src.type_simulator.type_simulator import TypeSimulator

def main():
    logging.basicConfig(level=logging.INFO)

    parser = TypeSimulatorParser()
    # new flag to select real GUI vs. headless (for E2E tests)
    parser.add_argument(
        "--window-mode", "-m",
        choices=["gui", "headless"],
        default="gui",
        help="whether to launch real GUI editor or headless (for E2E tests)",
    )
    args = parser.parse()

    simulator = TypeSimulator(
        editor_script_path=args.editor_script,
        file_path=args.file,
        text=args.text,
        typing_speed=args.speed,
        typing_variance=args.variance,
        window_mode=args.window_mode,
    )
    simulator.run()


if __name__ == "__main__":
    main()
