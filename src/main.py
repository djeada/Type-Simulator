# src/main.py
#!/usr/bin/env python3
import logging
import sys

from src.parser import TypeSimulatorParser
from src.type_simulator.type_simulator import TypeSimulator


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
    main()
