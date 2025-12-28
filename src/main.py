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
import time

from src.parser import TypeSimulatorParser


def print_profiles() -> None:
    """Print available typing profiles and exit."""
    from type_simulator.profiles import list_profiles

    print("\n🎹 Available Typing Profiles:\n")
    print("-" * 60)
    for name, profile in list_profiles().items():
        print(f"  {name:15} - {profile.description}")
        print(f"                  Speed: {profile.speed}s, Variance: {profile.variance}")
    print("-" * 60)
    print("\nUse with: --profile <name>")


def print_stats(text: str, start_time: float, end_time: float) -> None:
    """Print typing statistics."""
    duration = end_time - start_time
    char_count = len(text)
    word_count = len(text.split())

    # Calculate WPM (assuming average word length of 5 characters)
    if duration > 0:
        wpm = (char_count / 5) / (duration / 60)
        cps = char_count / duration
    else:
        wpm = 0
        cps = 0

    print("\n📊 Typing Statistics:")
    print("-" * 40)
    print(f"  Characters typed: {char_count}")
    print(f"  Words typed:      {word_count}")
    print(f"  Time elapsed:     {duration:.2f}s")
    print(f"  Speed:            {cps:.1f} chars/sec")
    print(f"  WPM:              {wpm:.1f}")
    print("-" * 40)


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

    # Handle --list-profiles
    if args.list_profiles:
        print_profiles()
        sys.exit(0)

    # Handle profile settings
    typing_speed = 0.15  # default
    typing_variance = 0.05  # default

    if args.profile:
        from type_simulator.profiles import get_profile

        profile = get_profile(args.profile)
        if profile:
            typing_speed = profile.speed
            typing_variance = profile.variance
            logging.info(f"Using profile '{args.profile}': speed={typing_speed}, variance={typing_variance}")

    # Override with explicit speed/variance if provided
    if args.speed is not None:
        typing_speed = args.speed
    if args.variance is not None:
        typing_variance = args.variance

    # Process text input first
    from utils.text_input import get_text_content

    try:
        if args.input is not None:
            text = get_text_content(args.input)
        else:
            text = get_text_content(None)  # fallback to STDIN
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    # Determine output file for direct mode
    output_file = args.output if args.mode == "direct" else None
    if args.mode == "direct" and not output_file:
        logging.error("In direct mode, --output must be specified.")
        sys.exit(2)

    # import the simulator only when actually running
    from type_simulator.type_simulator import TypeSimulator

    simulator = TypeSimulator(
        editor_script_path=args.editor_script,
        file_path=output_file,  # Only used in direct mode
        text=text,  # Already processed text
        typing_speed=typing_speed,
        typing_variance=typing_variance,
        wait=args.wait,
        mode=args.mode,
    )

    if args.dry_run:
        from type_simulator.validation import validate_inputs

        is_valid, errors, warnings = validate_inputs(
            args.mode, args.output, args.editor_script, text
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
    start_time = time.time()
    try:
        simulator.run()
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
        sys.exit(1)
    end_time = time.time()

    # Print statistics if requested
    if args.stats:
        print_stats(text, start_time, end_time)


if __name__ == "__main__":
    # ensure 'src' is on the import path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    main()
