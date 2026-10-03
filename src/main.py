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
    text: str,
    start_time: float,
    end_time: float,
    profile_name: str = None,
    show_speed: bool = True,
) -> None:
    """Print detailed typing statistics. Speed is omitted when nothing was typed."""
    duration = end_time - start_time
    char_count = len(text)
    word_count = len(text.split())
    line_count = text.count("\n") + 1

    # Calculate various metrics
    if duration > 0:
        wpm = (char_count / 5) / (duration / 60)
        cps = char_count / duration
    else:
        wpm = 0
        cps = 0

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
    if not show_speed:
        print("     Speed:           n/a (direct mode writes without typing)")
        print("=" * 50)
        return
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


def run_reel(args, text: str, pacing_values=None) -> None:
    """Render a reel video from parsed CLI arguments and exit on failure."""
    from pathlib import Path

    from type_simulator.reel import ReelConfig, render_reel
    from type_simulator.reel.timeline import Pacing

    try:
        width, height = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        logging.error(f"Invalid --size '{args.size}', expected WIDTHxHEIGHT")
        sys.exit(2)

    pacing = Pacing()
    if pacing_values:
        speed, variance, pause_probability, pause_duration = pacing_values
        pacing = Pacing(speed, variance, pause_probability, pause_duration)

    fake_output = None
    if args.fake_output:
        fake_output = Path(args.fake_output).expanduser().read_text(encoding="utf-8")

    script_path = None
    if args.input and Path(args.input).expanduser().is_file():
        script_path = Path(args.input).expanduser().resolve()

    music = None if (args.music or "").lower() == "none" else args.music
    config = ReelConfig(
        output=Path(args.output),
        script=text,
        script_path=script_path,
        filename=args.filename,
        theme=args.theme,
        prompt=args.prompt,
        title=args.title,
        subtitle=args.subtitle,
        footer=args.footer,
        size=(width, height),
        fps=args.fps,
        font=args.font,
        font_size=args.font_size,
        pacing=pacing,
        duration=args.duration,
        run=not args.no_run,
        run_command=args.run_cmd,
        fake_output=fake_output,
        run_timeout=args.run_timeout,
        music=music,
        music_volume=args.music_volume,
        key_sounds=not args.no_key_sounds,
        key_volume=args.key_volume,
        seed=args.seed,
        preview=args.preview,
    )
    try:
        result = render_reel(config)
    except (RuntimeError, ValueError, OSError) as e:
        logging.error(f"Reel rendering failed: {e}")
        sys.exit(1)
    if args.stats:
        print(f"🎬 {result.output}: {result.duration:.1f}s, {result.frames} frames")


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

    # Handle --check-terminals
    if args.check_terminals:
        from utils.utils import check_terminal_availability

        check_terminal_availability()
        sys.exit(0)

    # Handle profile settings
    typing_speed = 0.15  # default
    typing_variance = 0.05  # default
    pause_probability = 0.0
    pause_duration = 0.0

    if args.profile:
        from type_simulator.profiles import get_profile

        profile = get_profile(args.profile)
        if profile:
            typing_speed = profile.speed
            typing_variance = profile.variance
            pause_probability = profile.pause_probability
            pause_duration = profile.pause_duration
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
            # An explicit --input wins over a non-interactive stdin
            text = get_text_content(args.input, use_stdin=False)
        else:
            text = get_text_content(None)  # fallback to STDIN
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    # Determine output file for direct and reel modes
    output_file = args.output if args.mode in ("direct", "reel") else None
    if args.mode in ("direct", "reel") and not output_file:
        logging.error(f"In {args.mode} mode, --output must be specified.")
        sys.exit(2)

    if args.dry_run:
        from type_simulator.validation import validate_inputs

        is_valid, errors, warnings = validate_inputs(
            args.mode,
            output_file,
            args.editor_script,
            text,
            music=args.music if args.mode == "reel" else None,
        )
        for w in warnings:
            logging.warning(f"Validation warning: {w}")
        if is_valid:
            logging.info("Dry run validation successful")
            sys.exit(0)
        for e in errors:
            logging.error(f"Validation error: {e}")
        logging.error("Dry run validation failed")
        sys.exit(1)

    if args.mode == "reel":
        custom_pacing = (
            args.profile or args.speed is not None or args.variance is not None
        )
        run_reel(
            args,
            text,
            (
                (typing_speed, typing_variance, pause_probability, pause_duration)
                if custom_pacing
                else None
            ),
        )
        return

    # import the simulator only when actually running
    from type_simulator.type_simulator import TypeSimulator

    try:
        simulator = TypeSimulator(
            editor_script_path=args.editor_script,
            file_path=output_file,  # Only used in direct mode
            text=text,  # Already processed text
            resolve_text=False,
            typing_speed=typing_speed,
            typing_variance=typing_variance,
            wait=args.wait,
            mode=args.mode,
            geometry=args.geometry,
            pre_launch_cmd=args.pre_launch_cmd,
            pause_probability=pause_probability,
            pause_duration=pause_duration,
        )
    except (RuntimeError, ValueError) as e:
        logging.error(str(e))
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
        is_direct = args.mode == "direct"
        output_text = simulator.rendered_text if is_direct else text
        print_stats(
            output_text, start_time, end_time, args.profile, show_speed=not is_direct
        )


if __name__ == "__main__":
    # ensure 'src' is on the import path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    main()
