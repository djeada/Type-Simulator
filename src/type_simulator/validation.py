import logging
from pathlib import Path
import subprocess
from type_simulator.type_simulator import Mode
from type_simulator.text_typer import CommandParser

def validate_inputs(mode, file_path, editor_cmd, text):
    """
    Validate CLI inputs and text for Type-Simulator.
    Returns (is_valid, errors: list[str], warnings: list[str])
    """
    errors = []
    warnings = []

    # File checks
    if mode in [Mode.GUI, Mode.TERMINAL] and file_path:
        if not Path(file_path).exists():
            errors.append(f"File not found: {file_path}")
        elif Path(file_path).is_dir():
            errors.append(f"Not a file: {file_path}")
        elif not Path(file_path).is_file():
            errors.append(f"Not a file: {file_path}")

    # Editor command check
    if mode == Mode.GUI and editor_cmd:
        cmd = editor_cmd.split()[0]
        result = subprocess.run(['which', cmd], capture_output=True)
        if result.returncode != 0:
            errors.append(f"Editor command not found: {cmd}")

    # Text check
    if not text:
        errors.append("Input text is empty")
    else:
        # Capture warnings from CommandParser
        parser = CommandParser()
        parser_warnings = []
        class WarnCatcher(logging.Handler):
            def emit(self, record):
                if record.levelno == logging.WARNING:
                    parser_warnings.append(self.format(record))
        handler = WarnCatcher()
        logger = logging.getLogger('type_simulator.text_typer')
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
        try:
            parser.parse(text)
        finally:
            logger.removeHandler(handler)
        warnings.extend(parser_warnings)

    is_valid = not errors
    return is_valid, errors, warnings
