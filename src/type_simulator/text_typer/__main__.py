"""
TextTyper module for simulating human-like typing.

This module provides the core typing simulation functionality,
including support for various typing speeds, variance, and 
clipboard/backend strategies.
"""
import os
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
        lazy_init: bool = False
    ):
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance
        self.strict = strict
        self.backend = backend
        self.clipboard = None
        self.pynput = None
        self._initialized = False
        
        if not lazy_init:
            self._init_backend()
    
    def _init_backend(self) -> None:
        """Initialize the backend and clipboard when needed."""
        if self._initialized:
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
                logger.error("Token exec error: %s", e)


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
            lazy_init=lazy_init
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
