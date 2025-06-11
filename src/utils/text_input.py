"""Handle text input from various sources with priority handling.

This module provides functionality to read text content from multiple sources
(stdin, files, or literal text) with proper error handling and validation.
"""

import os
import sys
import select
import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Constants for input validation
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_STDIN_SIZE = 50 * 1024 * 1024  # 50MB
STDIN_TIMEOUT = 1.0  # seconds
SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1"]


class TextInputError(Exception):
    """Base exception for text input handling errors."""

    pass


class FileReadError(TextInputError):
    """Raised when there's an error reading from a file."""

    pass


class StdinReadError(TextInputError):
    """Raised when there's an error reading from stdin."""

    pass


class FileSizeError(TextInputError):
    """Raised when input size exceeds limits."""

    pass


def _read_stdin(timeout: float = STDIN_TIMEOUT, max_size: int = MAX_STDIN_SIZE) -> str:
    """Read from stdin with timeout and size limit."""
    try:
        # For testing with StringIO
        if not hasattr(sys.stdin, "fileno"):
            content = sys.stdin.read()
        else:
            # Real stdin with timeout (Unix-like systems only)
            if sys.platform != "win32" and hasattr(sys.stdin, "fileno"):
                try:
                    if not select.select([sys.stdin], [], [], timeout)[0]:
                        raise StdinReadError("Timeout reading from stdin")
                except (IOError, ValueError):
                    # Fall back to regular read if select fails
                    pass
            content = sys.stdin.read()

        if content is None or content == "":
            raise StdinReadError("Empty input from stdin")

        content_bytes = content.encode("utf-8")
        if len(content_bytes) > max_size:
            raise FileSizeError(f"Stdin input exceeds size limit of {max_size} bytes")

        return content
    except (IOError, OSError) as e:
        raise StdinReadError(f"Error reading from stdin: {e}") from e


def _read_file(path: Union[str, Path], max_size: int = MAX_FILE_SIZE) -> str:
    """Read file with size limit and encoding detection."""
    try:
        path = Path(path).expanduser().resolve()

        # Check file size before reading
        if path.stat().st_size > max_size:
            raise FileSizeError(f"File '{path}' exceeds size limit of {max_size} bytes")

        # Try different encodings
        for encoding in SUPPORTED_ENCODINGS:
            try:
                encoding_to_use = encoding
                if encoding == "utf-8-sig":
                    # Already handles BOM
                    content = path.read_text(encoding=encoding)
                else:
                    # For other encodings, we need to manually strip BOM
                    content = path.read_text(encoding=encoding)
                    content = content.lstrip("\ufeff")  # Remove BOM if present
                logger.debug(f"Successfully read file with {encoding} encoding")
                return content
            except UnicodeDecodeError:
                continue

        raise FileReadError(
            f"Could not decode file with supported encodings: {SUPPORTED_ENCODINGS}"
        )

    except PermissionError as e:
        raise FileReadError(f"Permission denied reading file '{path}'") from e
    except OSError as e:
        raise FileReadError(f"Error reading file '{path}': {e}") from e


def get_text_content(text_arg: Optional[str] = None) -> str:
    """
    Get text content from various sources in priority order:
    1. stdin (if available and has data)
    2. text argument (as file path or literal)

    Args:
        text_arg: Optional text argument that could be a file path or literal text

    Returns:
        str: The text content from the highest priority available source

    Raises:
        TextInputError: Base class for all text input related errors
        FileReadError: When there's an error reading from a file
        StdinReadError: When there's an error reading from stdin
        FileSizeError: When input size exceeds limits
        ValueError: If no text source is available
    """
    # If we have no text argument and no access to stdin, fail fast
    if text_arg is None and (
        not hasattr(sys, "stdin") or not hasattr(sys.stdin, "isatty")
    ):
        raise ValueError("No text source available. Provide text via --text or stdin.")

    stdin_available = False
    stdin_err = None

    # Only try stdin if we have access to it
    if hasattr(sys, "stdin") and hasattr(sys.stdin, "isatty"):
        try:
            if not sys.stdin.closed and not sys.stdin.isatty():
                stdin_available = True
                logger.debug("Attempting to read from stdin")
                try:
                    return _read_stdin()
                except (StdinReadError, FileSizeError) as e:
                    # Store the error for later if this is all we had
                    stdin_err = e
                    logger.warning(f"Failed to read from stdin: {e}")
                    # Fall through to try text_arg if available
        except (IOError, ValueError, AttributeError) as e:
            # Handle case where stdin is closed or otherwise unavailable
            logger.debug(f"Stdin not available: {e}")

    # No stdin or stdin failed, try text argument
    if text_arg:
        # Convert to Path and expand user dir
        path = Path(os.path.expanduser(text_arg))

        # Try as file path first
        if path.is_file():
            logger.debug(f"Attempting to read from file: {path}")
            try:
                return _read_file(path)
            except (FileReadError, FileSizeError) as e:
                logger.warning(f"Failed to read file: {e}")
                # Don't fall through - if it exists as a file but we can't read it,
                # that's an error
                raise

        # Not a file or doesn't exist, use as literal text
        logger.debug("Using provided text as literal")
        return text_arg

    # If we had no text_arg and tried stdin but it failed, raise that error
    if text_arg is None and stdin_available and stdin_err:
        raise stdin_err
    # If we have no text_arg and stdin wasn't even available, raise ValueError
    if text_arg is None:
        raise ValueError("No text source available. Provide text via --text or stdin.")
