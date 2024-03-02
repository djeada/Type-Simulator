import logging

from src.parser import TypeSimulatorParser
from src.type_simulator import TypeSimulator


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = TypeSimulatorParser()
    args = parser.parse()

    simulator = TypeSimulator(
        editor_script_path=args.editor_script,
        file_path=args.file,
        text=args.text,
        typing_speed=args.speed,
        typing_variance=args.variance,
    )
    simulator.run()
