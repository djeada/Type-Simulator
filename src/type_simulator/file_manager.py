# src/type_simulator/file_manager.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


class FileManager:
    """
    Thin wrapper around pathlib that guarantees the file exists and provides
    simple helpers for reading / writing text files.

    Parameters
    ----------
    file_path :
        Path-like or str.  If *None*, the user must call :py:meth:`set_path`
        before any I/O.
    create_if_missing :
        When *True* (default), an absent file is created as an empty UTF-8 text
        file so downstream code can safely open it for writing.
    """

    def __init__(self, file_path: Optional[str | Path] = None, *, create_if_missing: bool = True) -> None:
        self.file_path: Optional[Path] = (
            Path(file_path).expanduser().resolve() if file_path else None
        )
        self._create_if_missing = create_if_missing
        if self.file_path and create_if_missing:
            self._ensure_exists()

    # --------------------------------------------------------------------- #
    # Public helpers
    # --------------------------------------------------------------------- #
    def set_path(self, file_path: str | Path) -> None:
        """Set or replace the managed file path."""
        self.file_path = Path(file_path).expanduser().resolve()
        if self._create_if_missing:
            self._ensure_exists()

    def load_text(self, *, encoding: str = "utf-8") -> str:
        """
        Read the entire file and return its contents.

        Raises
        ------
        FileNotFoundError
            If the path is unset or the file is missing (and
            *create_if_missing* was False).
        """
        path = self._assert_path()
        with path.open("r", encoding=encoding) as fh:
            data = fh.read()
        logging.debug("Loaded %d characters from %s", len(data), path)
        return data

    def save_text(self, data: str, *, encoding: str = "utf-8") -> None:
        """Write *data* to the file, overwriting any existing content."""
        path = self._assert_path()
        with path.open("w", encoding=encoding) as fh:
            fh.write(data)
        logging.debug("Wrote %d characters to %s", len(data), path)

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #
    def _ensure_exists(self) -> None:
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.touch()
            logging.debug("Created file %s", self.file_path)

    def _assert_path(self) -> Path:
        if not self.file_path:
            raise FileNotFoundError("File path has not been set.")
        if not self.file_path.exists():
            raise FileNotFoundError(f"File '{self.file_path}' does not exist.")
        return self.file_path
