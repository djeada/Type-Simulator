#!/usr/bin/env python3
# src/main.py

"""
Type-Simulator entry point.

Patches sys.path for local imports, sets up logging,
and dispatches to the TypeSimulator class.
"""

import logging
import os
import sys

from src.parser import TypeSimulatorParser


def main() -> None:
    """
    Parse CLI args, configure logging, and run the simulator.
    """
    parser = TypeSimulatorParser()
    args = parser.parse()  # --version is handled here by argparse

    # configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Process text input first
    from utils.text_input import get_text_content

    try:
        if args.input is not None:
            text = args.input
        elif args.file_input is not None:
            text = args.file_input.read()
        else:
            text = get_text_content(None)  # fallback, should not happen due to parser
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    # import the simulator only when actually running
    from type_simulator.type_simulator import TypeSimulator

    simulator = TypeSimulator(
        editor_script_path=args.editor_script,
        file_path=args.file,
        text=text,  # Already processed text
        typing_speed=args.speed,
        typing_variance=args.variance,
        wait=args.wait,
        mode=args.mode,
    )

    if args.dry_run:
        from type_simulator.validation import validate_inputs

        is_valid, errors, warnings = validate_inputs(
            args.mode, args.file, args.editor_script, text
        )
        if is_valid:
            logging.info("Dry run validation successful")
            if warnings:
                for w in warnings:
                    logging.warning(f"Validation warning: {w}")
            sys.exit(0)
        else:
            for e in errors:
                logging.error(f"Validation error: {e}")
            for w in warnings:
                logging.warning(f"Validation warning: {w}")
            logging.error("Dry run validation failed")
            sys.exit(1)

    # Normal execution mode
    try:
        simulator.run()
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # ensure 'src' is on the import path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    main()
