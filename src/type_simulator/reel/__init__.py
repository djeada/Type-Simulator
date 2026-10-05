"""
Reel mode: render a vertical video (Reels / Shorts / TikTok) of a script being
typed into vim in a terminal, saved, executed, with key clicks and music.
Web pages (.html) are opened in a browser window instead, showing the live page,
and LaTeX (.tex) is typed next to a live PDF preview that updates line by line.

Frames are drawn with Pillow and encoded with ffmpeg, so no display, terminal
emulator or screen recorder is needed.
"""

import dataclasses
import logging
import random
import shutil
import subprocess
import tempfile
import time
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from type_simulator.reel import audio
from type_simulator.reel.browser import BROWSER_EXTENSIONS, PageCapture, capture_page
from type_simulator.reel.latex import LATEX_EXTENSIONS, build_preview
from type_simulator.reel.render import (
    FrameRenderer,
    browser_viewport,
    compute_layout,
    find_font,
    preview_viewport,
)
from type_simulator.reel.runner import (
    RunResult,
    default_run_command,
    exec_command,
    run_script,
)
from type_simulator.reel.themes import DEFAULT_THEME, THEMES, get_theme
from type_simulator.reel.timeline import (
    Pacing,
    Timeline,
    TimelineBuilder,
    colorize,
    fit_scale,
)

__all__ = ["ReelConfig", "ReelResult", "render_reel", "THEMES", "DEFAULT_THEME"]

logger = logging.getLogger(__name__)

BUILTIN_MUSIC = "builtin"


@dataclass
class ReelConfig:
    output: Path
    script: str
    script_path: Optional[Path] = None  # where the script lives, if it is a file
    filename: Optional[str] = None  # name shown on screen (defaults to file name)
    theme: str = DEFAULT_THEME
    prompt: Optional[str] = None  # e.g. "neo@matrix"; defaults to the theme's
    title: Optional[str] = None
    subtitle: Optional[str] = None
    footer: Optional[str] = None
    size: Tuple[int, int] = (1080, 1920)
    fps: int = 30
    font: Optional[str] = None
    font_size: Optional[int] = None
    pacing: Pacing = field(default_factory=Pacing)
    duration: Optional[float] = None  # fit typing so the reel lasts ~this long
    run: bool = True
    run_command: Optional[str] = None  # shown and executed; {file} = filename
    fake_output: Optional[str] = None  # shown instead of running the script
    run_timeout: float = 20.0
    music: Optional[str] = BUILTIN_MUSIC  # "builtin", a file path, or None
    music_volume: float = 0.35
    key_sounds: bool = True
    key_volume: float = 0.6
    seed: Optional[int] = None
    crf: int = 20
    preset: str = "medium"
    preview: bool = False  # write a single PNG frame instead of a video
    # Open the file in a browser instead of running it (default: for .html/.htm/.svg)
    browser: Optional[bool] = None
    browser_command: Optional[str] = None  # shown in the shell; {file} = filename
    browser_duration: float = 10.0  # seconds of live page before the closing hold
    browser_zoom: float = 1.0  # >1 renders the page larger (smaller CSS viewport)
    # Live PDF preview next to the editor for LaTeX files
    live_preview: bool = True
    latex_engine: str = "pdflatex"


@dataclass
class ReelResult:
    output: Path
    duration: float
    frames: int
    exit_code: Optional[int] = None


def _default_filename(script: str) -> str:
    first = script.splitlines()[0] if script else ""
    if "python" in first:
        return "hack.py"
    if "node" in first:
        return "hack.js"
    return "hack.sh"


def _default_command(cfg: ReelConfig, filename: str, script: str) -> str:
    if Path(filename).suffix.lower() in LATEX_EXTENSIONS:
        return f"{cfg.latex_engine} -interaction=nonstopmode {{file}}"
    return default_run_command(filename, script)


def _collect_output(cfg: ReelConfig, script: str, filename: str, cols: int, rows: int):
    """Return (command shown, output chunks, timed_out, exit_code)."""
    if cfg.fake_output is not None:
        command = (cfg.run_command or _default_command(cfg, filename, script)).format(
            file=filename
        )
        return command, [(0.0, cfg.fake_output)], False, None
    if not cfg.run:
        return None, [], False, None

    command = (cfg.run_command or _default_command(cfg, filename, script)).format(
        file=filename
    )
    path = cfg.script_path
    extra_env = None
    latex = Path(filename).suffix.lower() in LATEX_EXTENSIONS
    if latex and path and path.is_file():
        # Compile a copy, so the user's folder doesn't fill with .aux/.log files
        extra_env = {"TEXINPUTS": f"{path.parent.resolve()}:"}
    with tempfile.TemporaryDirectory(prefix="reel-run-") as tmp:
        if path and path.is_file() and path.name == filename and not latex:
            cwd = path.parent
        else:
            cwd = Path(tmp)
            path = cwd / filename
            path.write_text(script, encoding="utf-8")
            if script.startswith("#!"):
                path.chmod(0o755)
        result: RunResult = run_script(
            exec_command(command, path, script),
            cwd,
            cfg.run_timeout,
            cols,
            rows,
            extra_env=extra_env,
        )
    return command, result.chunks, result.timed_out, result.exit_code


def _page_url(theme, filename: str) -> str:
    user = theme.prompt.split("@")[0]
    home = "/root" if user == "root" else f"/home/{user}"
    return f"file://{home}/{filename}"


def _capture(
    cfg: ReelConfig, script: str, filename: str, layout, tmp: Path
) -> PageCapture:
    path = cfg.script_path
    if not (path and path.is_file() and path.name == filename):
        path = tmp / "site" / filename
        path.parent.mkdir()
        path.write_text(script, encoding="utf-8")
    x0, y0, x1, y1 = browser_viewport(layout)
    return capture_page(
        path,
        (x1 - x0, y1 - y0),
        cfg.fps,
        cfg.browser_duration + cfg.pacing.end_hold,
        tmp / "frames",
        zoom=cfg.browser_zoom,
    )


def _build_timeline(
    cfg,
    theme,
    rows,
    script,
    filename,
    command,
    chunks,
    timed_out,
    seed,
    page=None,
    latex=None,
):
    browser_command = None
    if page is not None:
        browser_command = (cfg.browser_command or "firefox {file}").format(
            file=filename
        )

    def build(pacing: Pacing) -> Timeline:
        builder = TimelineBuilder(
            theme,
            pacing,
            rows,
            seed=seed,
            preview_checkpoints=latex.checkpoints if latex else (),
        )
        return builder.build(
            script,
            filename,
            command,
            chunks,
            timed_out,
            browser_command=browser_command,
            browser_frames=page.count if page else 0,
            browser_fps=page.fps if page else cfg.fps,
        )

    timeline = build(cfg.pacing)
    if cfg.duration:
        scale = fit_scale(timeline, cfg.duration, cfg.pacing.scale)
        timeline = build(dataclasses.replace(cfg.pacing, scale=scale))
        logger.info("Typing scaled by %.2f to fit ~%ss", scale, cfg.duration)
    return timeline


def _audio_args(cfg: ReelConfig, timeline: Timeline, tmp: Path, seed: int) -> List[str]:
    """ffmpeg input and filter arguments for the soundtrack."""
    inputs: List[str] = []
    filters: List[str] = []
    labels: List[str] = []
    dur = timeline.duration
    index = 1  # input 0 is the video pipe

    if cfg.key_sounds and timeline.sounds:
        clicks = tmp / "clicks.wav"
        audio.write_wav(clicks, audio.render_clicks(timeline.sounds, dur, seed))
        inputs += ["-i", str(clicks)]
        filters.append(f"[{index}:a]volume={cfg.key_volume}[keys]")
        labels.append("[keys]")
        index += 1

    if cfg.music:
        if cfg.music == BUILTIN_MUSIC:
            music = tmp / "music.wav"
            logger.info("Synthesizing music track")
            audio.write_wav(music, audio.render_music(dur, seed))
        else:
            music = Path(cfg.music).expanduser()
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        fade_out = max(0.0, dur - 2.5)
        filters.append(
            f"[{index}:a]atrim=0:{dur:.3f},volume={cfg.music_volume},"
            f"afade=t=in:d=1.5,afade=t=out:st={fade_out:.3f}:d=2.5[music]"
        )
        labels.append("[music]")
        index += 1

    if not labels:
        return ["-an"]
    if len(labels) == 1:
        mix = f"{labels[0]}alimiter=limit=0.95[aout]"
    else:
        mix = f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95[aout]"
    filters.append(mix)
    return inputs + [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
    ]


def render_reel(cfg: ReelConfig) -> ReelResult:
    """Render the reel described by `cfg` to `cfg.output`."""
    with tempfile.TemporaryDirectory(prefix="reel-") as tmp:
        return _render(cfg, Path(tmp))


def _render(cfg: ReelConfig, tmp: Path) -> ReelResult:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg and not cfg.preview:
        raise RuntimeError("ffmpeg is required for reel mode; please install it.")

    seed = cfg.seed if cfg.seed is not None else random.randrange(1 << 30)
    # Typed without a dangling empty last line; saved/run with a final newline
    script = cfg.script.replace("\r\n", "\n").expandtabs(4).rstrip()
    filename = cfg.filename or (cfg.script_path.name if cfg.script_path else None)
    filename = filename or _default_filename(script)
    use_browser = cfg.browser
    if use_browser is None:
        use_browser = Path(filename).suffix.lower() in BROWSER_EXTENSIONS
    use_latex = (
        cfg.live_preview
        and not use_browser
        and Path(filename).suffix.lower() in LATEX_EXTENSIONS
    )

    theme = get_theme(cfg.theme)
    if cfg.prompt:
        theme = dataclasses.replace(theme, prompt=cfg.prompt)

    mono = cfg.font or find_font("monospace")
    layout = compute_layout(cfg.size[0], cfg.size[1], cfg.font_size, mono, use_latex)
    logger.info("Terminal is %d columns x %d rows", layout.cols, layout.rows)

    latex = None
    if use_latex:
        x0, y0, x1, y1 = preview_viewport(layout)
        texinputs = cfg.script_path.parent.resolve() if cfg.script_path else None
        latex = build_preview(
            script,
            (x1 - x0, y1 - y0),
            tmp / "preview",
            cfg.latex_engine,
            texinputs,
            colors=(theme.window_bg, theme.fg, theme.accent),
        )
    page = None
    if use_browser:
        page = _capture(cfg, script + "\n", filename, layout, tmp)
        command, chunks, timed_out, exit_code = None, [], False, None
    else:
        command, chunks, timed_out, exit_code = _collect_output(
            cfg, script + "\n", filename, layout.cols, layout.rows
        )
    timeline = _build_timeline(
        cfg,
        theme,
        layout.rows,
        script,
        filename,
        command,
        chunks,
        timed_out,
        seed,
        page,
        latex,
    )
    renderer = FrameRenderer(
        theme,
        layout,
        script,
        colorize(script, filename, theme),
        filename,
        title=cfg.title,
        subtitle=cfg.subtitle,
        footer=cfg.footer,
        mono_path=mono,
        mono_bold_path=None if cfg.font else find_font("monospace:bold"),
        title_font_path=find_font("sans:bold"),
        ui_font_path=find_font("sans"),
        capture=page,
        url=_page_url(theme, filename),
        latex=latex,
        preview_title=f"{Path(filename).stem}.pdf",
    )

    times = [t for t, _ in timeline.keyframes]
    total_frames = int(timeline.duration * cfg.fps) + 1
    logger.info(
        "Reel: %.1fs, %d frames at %dfps, %d keyframes",
        timeline.duration,
        total_frames,
        cfg.fps,
        len(times),
    )

    def frame_at(t: float):
        idx = max(0, bisect_right(times, t) - 1)
        since = t - times[idx]
        cursor_on = since < 0.5 or (t % 1.0) < 0.55
        return idx, cursor_on

    output = Path(cfg.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)

    if cfg.preview:
        # Partway through typing (editor with highlighted code), or the live page
        if page is not None:
            t = timeline.duration - cfg.browser_duration * 0.5
        else:
            t = timeline.duration * 0.45
        idx, _ = frame_at(t)
        img = renderer.render(timeline.keyframes[idx][1], True)
        renderer.draw_progress(img, t / timeline.duration)
        img.save(output)
        return ReelResult(output, timeline.duration, 1, exit_code)

    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{layout.width}x{layout.height}", "-r", str(cfg.fps),
        "-i", "-",
    ]  # fmt: skip
    cmd += _audio_args(cfg, timeline, tmp, seed)
    cmd += [
        "-c:v", "libx264", "-preset", cfg.preset, "-crf", str(cfg.crf),
        "-pix_fmt", "yuv420p", "-r", str(cfg.fps),
        "-t", f"{timeline.duration:.3f}",
        "-movflags", "+faststart",
        str(output),
    ]  # fmt: skip
    logger.debug("ffmpeg command: %s", " ".join(cmd))
    stderr_path = tmp / "ffmpeg.log"
    with open(stderr_path, "wb") as stderr:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=stderr)
        cache_key, cached = None, None
        started = time.monotonic()
        try:
            for f in range(total_frames):
                t = f / cfg.fps
                key = frame_at(t)
                if key != cache_key:
                    cached = renderer.render(timeline.keyframes[key[0]][1], key[1])
                    cache_key = key
                img = cached.copy()
                renderer.draw_progress(img, t / timeline.duration)
                proc.stdin.write(img.tobytes())
                if f and f % (cfg.fps * 10) == 0:
                    logger.info(
                        "Rendered %d/%d frames (%.0f%%, %.1fs elapsed)",
                        f,
                        total_frames,
                        100 * f / total_frames,
                        time.monotonic() - started,
                    )
            proc.stdin.close()
        except BrokenPipeError:
            pass
        code = proc.wait()
    if code != 0:
        raise RuntimeError(
            f"ffmpeg failed ({code}): {stderr_path.read_text(errors='replace')[-2000:]}"
        )

    logger.info("Wrote %s (%.1fs)", output, timeline.duration)
    return ReelResult(output, timeline.duration, total_frames, exit_code)
