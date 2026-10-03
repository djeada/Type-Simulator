"""
TextTyper module for simulating human-like typing.

This module provides the core typing simulation functionality,
including support for various typing speeds, variance, and
clipboard/backend strategies.
"""

import os
import random
import time
import logging
from typing import List, Optional, Any

from type_simulator.text_typer.clipboard import (
    PyperclipClipboard,
    PlatformClipboard,
    TkClipboard,
)
from type_simulator.text_typer.parser import CommandParser
from type_simulator.text_typer.token import Token

logger = logging.getLogger(__name__)


def _get_pyautogui():
    """Lazily import pyautogui only when needed."""
    import pyautogui

    return pyautogui


# ─────────────────────── Render backend ───────────────────────
class RenderBackend:
    """
    Backend that records the text a token stream would produce instead of
    sending keystrokes. Used by direct mode to expand macros without a display.
    """

    _KEY_TEXT = {"enter": "\n", "return": "\n", "tab": "\t", "space": " "}

    def __init__(self) -> None:
        self._parts: List[str] = []

    @property
    def text(self) -> str:
        return "".join(self._parts)

    def write(self, text: str, interval: float = 0.0) -> None:
        self._parts.append(text)

    def press(self, key: str) -> None:
        if key in self._KEY_TEXT:
            self._parts.append(self._KEY_TEXT[key])
        else:
            logger.debug("Ignoring key '%s' while rendering", key)

    def hotkey(self, *keys: str) -> None:
        if len(keys) == 1:
            self.press(keys[0])
        else:
            logger.debug("Ignoring hotkey %s while rendering", "+".join(keys))

    def moveTo(self, *args, **kwargs) -> None:
        logger.debug("Ignoring mouse move while rendering")

    def click(self, *args, **kwargs) -> None:
        logger.debug("Ignoring mouse click while rendering")


# ─────────────────────────── Typist ───────────────────────────
class Typist:
    """
    Executes typing tokens using the configured backend.

    Attributes:
        typing_speed: Base seconds per character
        typing_variance: Random variance in timing
        backend: The GUI automation backend (pyautogui by default)
        clipboard: The clipboard strategy to use
        pynput: Optional pynput keyboard controller
        strict: Whether to raise errors on invalid sequences
    """

    def __init__(
        self,
        typing_speed: float = 0.15,
        typing_variance: float = 0.05,
        backend: Optional[Any] = None,
        strict: bool = False,
        lazy_init: bool = False,
        pause_probability: float = 0.0,
        pause_duration: float = 0.0,
    ):
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance
        self.strict = strict
        self.backend = backend
        self.clipboard = None
        self.pynput = None
        self.pause_probability = pause_probability
        self.pause_duration = pause_duration
        self.render_only = isinstance(backend, RenderBackend)
        self._initialized = False

        if not lazy_init:
            self._init_backend()

    def _init_backend(self) -> None:
        """Initialize the backend and clipboard when needed."""
        if self._initialized:
            return

        if self.render_only:
            self._initialized = True
            return

        if self.backend is None:
            if "DISPLAY" not in os.environ and os.name != "nt":
                raise RuntimeError("No DISPLAY; use Xvfb or supply backend")
            self.backend = _get_pyautogui()

        # clipboard: try pyperclip, platform, tk
        for strat in (PyperclipClipboard, PlatformClipboard, TkClipboard):
            try:
                self.clipboard = strat()
                logger.info("Using %s clipboard", strat.__name__)
                break
            except Exception as e:
                logger.debug("%s unavailable: %s", strat.__name__, e)

        try:
            from pynput.keyboard import Controller as PC

            self.pynput = PC()
            logger.info("Using pynput")
        except Exception:
            self.pynput = None

        self._initialized = True

    def execute(self, toks: List[Token]) -> None:
        """Execute a list of tokens."""
        # Ensure backend is initialized before executing
        self._init_backend()

        for t in toks:
            try:
                t.execute(self)
            except Exception as e:
                if self.strict:
                    raise
                logger.error("Token exec error: %s", e)

    def maybe_pause(self) -> None:
        """Randomly pause between words, as configured by the typing profile."""
        if self.render_only or self.pause_probability <= 0:
            return
        if random.random() < self.pause_probability:
            pause = self.pause_duration * random.uniform(0.5, 1.5)
            logger.debug("Micro-pause for %.2fs", pause)
            time.sleep(pause)


# ─────────────────────────── Facade ───────────────────────────
class TextTyper:
    """
    Facade for parsing and executing typing commands.

    This class provides a high-level interface for simulating typing,
    including support for macros, special keys, and various typing profiles.

    Attributes:
        text: The text to type (can include macros)
        typing_speed: Base seconds per character
        typing_variance: Random variance in timing
        backend: The GUI automation backend
        strict: Whether to raise errors on invalid sequences
    """

    def __init__(
        self,
        text: str,
        typing_speed: float = 0.15,
        typing_variance: float = 0.05,
        backend: Optional[Any] = None,
        strict: bool = False,
        lazy_init: bool = False,
        pause_probability: float = 0.0,
        pause_duration: float = 0.0,
    ):
        self.text = text
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance
        self.backend = backend
        self.strict = strict
        self._lazy_init = lazy_init
        self._parser = CommandParser(strict)
        self._typist = Typist(
            typing_speed,
            typing_variance,
            backend,
            strict,
            lazy_init=lazy_init,
            pause_probability=pause_probability,
            pause_duration=pause_duration,
        )
        # Only set backend immediately if not using lazy initialization
        if not lazy_init and self.backend is None:
            self.backend = self._typist.backend

    def simulate_typing(self) -> None:
        """Parse and execute the text with typing simulation."""
        # Ensure backend is available when we start typing
        if self.backend is None and self._lazy_init:
            self._typist._init_backend()
            self.backend = self._typist.backend

        toks = self._parser.parse(self.text)
        logger.info("Parsed %d tokens", len(toks))
        self._typist.execute(toks)

    def render(self) -> str:
        """
        Expand macros into the plain text they would type, without touching
        the keyboard. Keys other than enter/tab, mouse actions and waits are
        ignored.
        """
        typist = Typist(backend=RenderBackend(), strict=self.strict)
        typist.execute(self._parser.parse(self.text or ""))
        return typist.backend.text
