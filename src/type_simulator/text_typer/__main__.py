import os
import logging

from src.type_simulator.text_typer.clipboard import (
    PyperclipClipboard,
    PlatformClipboard,
    TkClipboard,
)
from src.type_simulator.text_typer.parser import CommandParser
from src.type_simulator.text_typer.token import Token

logger = logging.getLogger(__name__)


# ─────────────────────────── Typist ───────────────────────────
class Typist:
    def __init__(
        self, typing_speed=0.15, typing_variance=0.05, backend=None, strict=False
    ):
        self.typing_speed, self.typing_variance = typing_speed, typing_variance
        if backend is None:
            if "DISPLAY" not in os.environ and os.name != "nt":
                raise RuntimeError("No DISPLAY; use Xvfb or supply backend")
            import pyautogui as pg

            backend = pg
        self.backend = backend
        # clipboard: try pyperclip, platform, tk
        self.clipboard = None
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
        self.strict = strict

    def execute(self, toks: list[Token]):
        for t in toks:
            try:
                t.execute(self)
            except Exception as e:
                logger.error("Token exec error: %s", e)


# ─────────────────────────── Facade ───────────────────────────
class TextTyper:
    def __init__(
        self,
        text: str,
        typing_speed=0.15,
        typing_variance=0.05,
        backend=None,
        strict=False,
    ):
        self.text = text
        self.typing_speed = typing_speed
        self.typing_variance = typing_variance
        self.backend = backend
        self.strict = strict
        self._parser = CommandParser(strict)
        self._typist = Typist(typing_speed, typing_variance, backend, strict)
        if self.backend is None:
            self.backend = self._typist.backend

    def simulate_typing(self):
        toks = self._parser.parse(self.text)
        logger.info("Parsed %d tokens", len(toks))
        self._typist.execute(toks)
