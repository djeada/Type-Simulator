import logging
import shlex
import shutil
from pathlib import Path

from type_simulator.type_simulator import Mode
from type_simulator.text_typer.parser import CommandParser


def validate_inputs(
    mode, file_path, editor_cmd, text, music=None, browser=False, latex_engine=None
):
    """
    Validate CLI inputs and text for Type-Simulator.

    ``mode`` may be a :class:`Mode` or its string value (as passed by the CLI).
    ``music`` is only checked in reel mode ('builtin', 'none' or a file path),
    as is ``browser`` (whether the reel opens the file in a browser) and
    ``latex_engine`` (set when the reel shows a live LaTeX preview).
    Returns (is_valid, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []
    mode = Mode(mode) if isinstance(mode, str) else mode

    # File checks
    if mode in [Mode.GUI, Mode.TERMINAL] and file_path:
        if not Path(file_path).exists():
            errors.append(f"File not found: {file_path}")
        elif not Path(file_path).is_file():
            errors.append(f"Not a file: {file_path}")

    if mode == Mode.DIRECT:
        if not file_path:
            errors.append("Direct mode requires an output file")
        elif Path(file_path).is_dir():
            errors.append(f"Not a file: {file_path}")

    if mode == Mode.REEL:
        if not file_path:
            errors.append("Reel mode requires an output file")
        if shutil.which("ffmpeg") is None:
            errors.append("ffmpeg not found; it is required for reel mode")
        if music and music.lower() not in ("builtin", "none"):
            if not Path(music).expanduser().is_file():
                errors.append(f"Music file not found: {music}")
        if browser:
            from type_simulator.reel.browser import INSTALL_HINT, playwright_available

            if not playwright_available():
                errors.append(INSTALL_HINT)
        if latex_engine:
            from type_simulator.reel.latex import tools_available

            missing = tools_available(latex_engine)
            if missing:
                errors.append(f"LaTeX live preview needs: {', '.join(missing)}")
        # The script is typed verbatim, so macros aren't parsed here
        if not text:
            errors.append("Input text is empty")
        return not errors, errors, warnings

    # Editor command check
    if mode == Mode.GUI and editor_cmd:
        try:
            cmd = shlex.split(editor_cmd)[0]
        except (ValueError, IndexError):
            errors.append(f"Invalid editor command: {editor_cmd!r}")
        else:
            if shutil.which(cmd) is None:
                errors.append(f"Editor command not found: {cmd}")

    # Text check
    if not text:
        errors.append("Input text is empty")
    else:
        # Strict parsing reports invalid or unbalanced macros as warnings
        parser = CommandParser(strict=True)
        parser_warnings = []

        class WarnCatcher(logging.Handler):
            def emit(self, record):
                if record.levelno >= logging.WARNING:
                    parser_warnings.append(record.getMessage())

        handler = WarnCatcher(level=logging.WARNING)
        logger = logging.getLogger("type_simulator.text_typer")
        previous_level, previous_propagate = logger.level, logger.propagate
        # Collect warnings here only; the caller decides how to report them
        logger.propagate = False
        logger.addHandler(handler)
        if logger.getEffectiveLevel() > logging.WARNING:
            logger.setLevel(logging.WARNING)
        try:
            parser.parse(text)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)
            logger.propagate = previous_propagate
        warnings.extend(parser_warnings)

    is_valid = not errors
    return is_valid, errors, warnings
