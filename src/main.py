import logging

from src.parser import TypeSimulatorParser
from src.type_simulator import TypeSimulator


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = TypeSimulatorParser()
    args = parser.parse()

    simulator = TypeSimulator(
        editor_script=args.editor_script,
        file=args.file,
        text=args.text,
        speed=args.speed,
        variance=args.variance,
    )
    simulator.run()
