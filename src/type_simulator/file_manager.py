from pathlib import Path
from typing import Optional


class FileManager:
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = Path(file_path).resolve() if file_path else None

    def load_text(self) -> str:
        if not self.file_path or not self.file_path.exists():
            raise FileNotFoundError(f"File '{self.file_path}' does not exist.")
        with self.file_path.open("r") as file:
            return file.read()
