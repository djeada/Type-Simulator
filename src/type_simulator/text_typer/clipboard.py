import os
import shutil
import subprocess
from abc import ABC, abstractmethod


# ─────────────────────── Clipboard Strategies ───────────────────────
class ClipboardStrategy(ABC):
    @abstractmethod
    def copy(self, text: str) -> None: ...
    @abstractmethod
    def paste(self) -> str: ...


class PyperclipClipboard(ClipboardStrategy):
    def __init__(self):
        import pyperclip as pc

        self._clip = pc
        self._clip.copy("")
        _ = self._clip.paste()

    def copy(self, text: str):
        self._clip.copy(text)

    def paste(self) -> str:
        return self._clip.paste()


class PlatformClipboard(ClipboardStrategy):
    def __init__(self):
        self.cmds = self._detect()
        if not self.cmds:
            raise RuntimeError("No platform clipboard commands")

    @staticmethod
    def _detect():
        c = {}
        if shutil.which("pbcopy") and shutil.which("pbpaste"):
            c["copy"], c["paste"] = ["pbcopy"], ["pbpaste"]
        elif shutil.which("xclip"):
            c["copy"] = ["xclip", "-selection", "clipboard"]
            c["paste"] = ["xclip", "-selection", "clipboard", "-o"]
        elif shutil.which("xsel"):
            c["copy"] = ["xsel", "--clipboard", "--input"]
            c["paste"] = ["xsel", "--clipboard", "--output"]
        elif os.name == "nt" and shutil.which("clip"):
            c["copy"] = ["clip"]  # no fast native paste on Win
        return c

    def copy(self, text: str):
        if "copy" not in self.cmds:
            raise RuntimeError("No copy cmd")
        proc = subprocess.Popen(self.cmds["copy"], stdin=subprocess.PIPE)
        proc.communicate(input=text.encode())

    def paste(self) -> str:
        if "paste" not in self.cmds:
            raise RuntimeError("No paste cmd")
        return subprocess.check_output(self.cmds["paste"]).decode()


class TkClipboard(ClipboardStrategy):
    def __init__(self):
        import tkinter as tk

        self._tk = tk.Tk()
        self._tk.withdraw()
        self.copy("")
        _ = self.paste()

    def copy(self, text: str):
        self._tk.clipboard_clear()
        self._tk.clipboard_append(text)
        self._tk.update()

    def paste(self) -> str:
        self._tk.update()
        return self._tk.clipboard_get()
