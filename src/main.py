# src/main.py
#!/usr/bin/env python3
import logging
import sys
import os

from src.parser import TypeSimulatorParser


def main():
    parser = TypeSimulatorParser()
    args = parser.parse()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    simulator = TypeSimulator(
        editor_script_path=args.editor_script,
        file_path=args.file,
        text=args.text,
        typing_speed=args.speed,
        typing_variance=args.variance,
        wait=args.wait,
    )
    simulator.run()


if __name__ == "__main__":
    # Patch sys.path for src import compatibility
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from type_simulator.type_simulator import TypeSimulator

    main()
