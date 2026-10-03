"""Run the typed script for real and record when each piece of output arrived."""

import codecs
import logging
import os
import shlex
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Interpreter used for a file extension when the script has no shebang
INTERPRETERS = {
    ".py": "python3",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".js": "node",
    ".mjs": "node",
    ".ts": "npx tsx",
    ".rb": "ruby",
    ".pl": "perl",
    ".php": "php",
    ".lua": "lua",
    ".r": "Rscript",
}


@dataclass
class RunResult:
    # (seconds since start, decoded output chunk)
    chunks: List[Tuple[float, str]] = field(default_factory=list)
    exit_code: Optional[int] = None
    timed_out: bool = False
    duration: float = 0.0


# Compiled languages: compile, then run the binary
COMPILERS = {
    ".c": "gcc {file} -o {stem} -lm && ./{stem}",
    ".cpp": "g++ {file} -o {stem} && ./{stem}",
    ".cc": "g++ {file} -o {stem} && ./{stem}",
    ".rs": "rustc {file} -o {stem} && ./{stem}",
    ".go": "go run {file}",
}


def default_run_command(filename: str, text: str) -> str:
    """
    Pick the command a user would type to run `filename`, e.g. 'python3 hack.py'.
    """
    ext = Path(filename).suffix.lower()
    if ext in COMPILERS:
        return COMPILERS[ext].format(file=filename, stem=Path(filename).stem)
    if ext in INTERPRETERS:
        return f"{INTERPRETERS[ext]} {filename}"
    if _shebang(text):
        return f"./{filename}"
    return f"bash {filename}"


def _shebang(text: str) -> Optional[str]:
    first = text.splitlines()[0] if text else ""
    return first[2:].strip() if first.startswith("#!") else None


def exec_command(display_command: str, script: Path, text: str) -> str:
    """
    The command actually executed. './script' is shown on screen, but if the
    file isn't executable it is run through its shebang interpreter instead.
    """
    if display_command.startswith("./") and not os.access(script, os.X_OK):
        interpreter = _shebang(text) or "bash"
        return f"{interpreter} {shlex.quote(str(script))}"
    return display_command


def run_script(
    command: str,
    cwd: Path,
    timeout: float,
    columns: int,
    rows: int,
) -> RunResult:
    """
    Execute `command` in `cwd`, capturing stdout+stderr chunks with timestamps.
    The process is killed after `timeout` seconds.
    """
    env = dict(os.environ)
    env.update(
        {
            "TERM": "xterm-256color",
            "COLUMNS": str(columns),
            "LINES": str(rows),
            "PYTHONUNBUFFERED": "1",
            "FORCE_COLOR": "1",
            "CLICOLOR_FORCE": "1",
        }
    )
    logger.info("Running script: %s (cwd=%s)", command, cwd)
    result = RunResult()
    start = time.monotonic()
    # Through a shell when possible, so commands like 'gcc x.c && ./x' work
    bash = shutil.which("bash")
    argv = [bash, "-c", command] if bash else shlex.split(command)
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=hasattr(os, "killpg"),
    )

    def reader() -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        fd = proc.stdout.fileno()
        while True:
            data = os.read(fd, 4096)
            if not data:
                break
            text = decoder.decode(data)
            if text:
                result.chunks.append((time.monotonic() - start, text))
        tail = decoder.decode(b"", final=True)
        if tail:
            result.chunks.append((time.monotonic() - start, tail))

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.warning("Script still running after %ss; stopping it", timeout)
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        proc.wait()
        result.timed_out = True
    thread.join(timeout=2)
    proc.stdout.close()
    result.exit_code = proc.returncode
    result.duration = time.monotonic() - start
    logger.info(
        "Script finished with code %s in %.2fs (%d output chunks)",
        result.exit_code,
        result.duration,
        len(result.chunks),
    )
    return result
