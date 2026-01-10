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
    """Print available typing profiles with detailed information."""
    from type_simulator.profiles import list_profiles

    print("\n🎹 Available Typing Profiles:\n")
    print("=" * 70)
    print(f"{'Profile':<15} {'Speed':>8} {'Variance':>10} {'Description':<35}")
    print("=" * 70)
    for name, profile in list_profiles().items():
        print(
            f"  {name:<13} {profile.speed:>6.3f}s  ±{profile.variance:<8.3f} {profile.description}"
        )
    print("=" * 70)
    print(
        '\n💡 Usage: python -m src.main --profile <name> --mode <mode> --input "text"'
    )
    print(
        '   Example: python -m src.main --profile programmer --mode direct --output code.txt --input "Hello World!"'
    )


def print_stats(
    text: str, start_time: float, end_time: float, profile_name: str = None
) -> None:
    """Print detailed typing statistics."""
    duration = end_time - start_time
    char_count = len(text)
    word_count = len(text.split())
    line_count = text.count("\n") + 1

    # Calculate various metrics
    if duration > 0:
        wpm = (char_count / 5) / (duration / 60)
        cps = char_count / duration
        wps = word_count / duration * 60 if duration > 0 else 0
    else:
        wpm = 0
        cps = 0
        wps = 0

    # Character breakdown
    alpha_count = sum(1 for c in text if c.isalpha())
    digit_count = sum(1 for c in text if c.isdigit())
    space_count = text.count(" ")
    special_count = char_count - alpha_count - digit_count - space_count

    print("\n" + "=" * 50)
    print("📊 TYPING STATISTICS")
    print("=" * 50)

    if profile_name:
        print(f"  🎹 Profile Used:    {profile_name}")
        print("-" * 50)

    print("  📝 Content Summary:")
    print(f"     Characters:      {char_count:,}")
    print(f"     Words:           {word_count:,}")
    print(f"     Lines:           {line_count:,}")
    print("-" * 50)

    print("  📈 Character Breakdown:")
    print(
        f"     Letters:         {alpha_count:,} ({alpha_count/char_count*100:.1f}%)"
        if char_count > 0
        else "     Letters:         0"
    )
    print(
        f"     Digits:          {digit_count:,} ({digit_count/char_count*100:.1f}%)"
        if char_count > 0
        else "     Digits:          0"
    )
    print(
        f"     Spaces:          {space_count:,} ({space_count/char_count*100:.1f}%)"
        if char_count > 0
        else "     Spaces:          0"
    )
    print(
        f"     Special:         {special_count:,} ({special_count/char_count*100:.1f}%)"
        if char_count > 0
        else "     Special:         0"
    )
    print("-" * 50)

    print("  ⏱️  Performance:")
    print(f"     Time Elapsed:    {duration:.2f}s")
    print(f"     Speed (CPS):     {cps:.1f} chars/sec")
    print(f"     Speed (WPM):     {wpm:.1f} words/min")
    print("=" * 50)

    # Fun comparison
    if wpm > 0:
        if wpm > 200:
            print("  🚀 Speed Rating: LIGHTNING FAST!")
        elif wpm > 100:
            print("  ⚡ Speed Rating: Very Fast")
        elif wpm > 60:
            print("  ✨ Speed Rating: Professional")
        elif wpm > 40:
            print("  👍 Speed Rating: Average")
        else:
            print("  🐢 Speed Rating: Careful & Deliberate")


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
            logging.info(
                f"Using profile '{args.profile}': speed={typing_speed}, variance={typing_variance}"
            )

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
        print_stats(text, start_time, end_time, args.profile)


if __name__ == "__main__":
    # ensure 'src' is on the import path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    main()
