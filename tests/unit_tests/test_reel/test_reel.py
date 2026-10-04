import shutil
import subprocess
import sys

import pytest

from type_simulator.reel import ReelConfig, render_reel
from type_simulator.reel.runner import default_run_command, exec_command, run_script
from type_simulator.reel.terminal import TerminalBuffer
from type_simulator.reel.themes import THEMES, get_theme
from type_simulator.reel.timeline import (
    EDITOR,
    SHELL,
    Pacing,
    TimelineBuilder,
    colorize,
    fit_scale,
)

THEME = get_theme("hacker")


def _text(term: TerminalBuffer):
    return ["".join(run[0] for run in line) for line in term.lines]


# ─────────────────────────── terminal ───────────────────────────
def test_terminal_colors_and_newlines():
    term = TerminalBuffer(THEME.ansi)
    term.feed("plain \x1b[31mred\x1b[0m\nnext")
    assert _text(term) == ["plain red", "next"]
    assert term.lines[0][1] == ("red", THEME.ansi[1], False)


def test_terminal_carriage_return_redraws_line():
    term = TerminalBuffer(THEME.ansi)
    for pct in ("10%", "50%", "100%"):
        term.feed(f"\rloading {pct}")
    term.feed("\ndone")
    assert _text(term) == ["loading 100%", "done"]


def test_terminal_escape_split_across_chunks():
    term = TerminalBuffer(THEME.ansi)
    term.feed("a\x1b[3")
    term.feed("2mb")
    assert _text(term) == ["ab"]
    assert term.lines[0][-1][1] == THEME.ansi[2]


def test_terminal_clear_and_256_colors():
    term = TerminalBuffer(THEME.ansi)
    term.feed("old\n\x1b[2Jnew \x1b[38;5;196mx\x1b[38;2;1;2;3my")
    assert _text(term) == ["new xy"]
    assert term.lines[0][1][1] == (255, 0, 0)
    assert term.lines[0][2][1] == (1, 2, 3)


# ─────────────────────────── runner ───────────────────────────
def test_default_run_command():
    assert default_run_command("a.py", "") == "python3 a.py"
    assert default_run_command("tool", "#!/usr/bin/env python3\n") == "./tool"
    assert default_run_command("tool", "echo hi") == "bash tool"


def test_exec_command_uses_shebang_when_not_executable(tmp_path):
    script = tmp_path / "tool"
    script.write_text("#!/usr/bin/env python3\nprint(1)\n")
    assert exec_command("./tool", script, script.read_text()).startswith(
        "/usr/bin/env python3"
    )


def test_run_script_captures_output_and_times_out(tmp_path):
    ok = run_script(f"{sys.executable} -c \"print('hi')\"", tmp_path, 10, 40, 10)
    assert ok.exit_code == 0
    assert "".join(c for _, c in ok.chunks).strip() == "hi"

    slow = run_script(
        f'{sys.executable} -c "import time; time.sleep(30)"', tmp_path, 0.5, 40, 10
    )
    assert slow.timed_out


# ─────────────────────────── timeline ───────────────────────────
def _build(script="print(1)\nx = 2", chunks=((0.0, "1\n"),), pacing=None):
    builder = TimelineBuilder(THEME, pacing or Pacing(), rows=20, seed=3)
    return builder.build(script, "a.py", "python3 a.py", list(chunks))


def test_timeline_story_order():
    tl = _build()
    modes = [scene.mode for _, scene in tl.keyframes]
    assert modes[0] == SHELL
    first_editor = modes.index(EDITOR)
    assert SHELL in modes[first_editor:]
    times = [t for t, _ in tl.keyframes]
    assert times == sorted(times)
    assert tl.duration > times[-1]
    final = tl.keyframes[-1][1].shell
    lines = ["".join(r[0] for r in line) for line in final]
    assert lines == [
        "root@kali:~# vim a.py",
        "root@kali:~# python3 a.py",
        "1",
        "root@kali:~# ",
    ]


def test_timeline_editor_reaches_full_script_and_autoindents():
    script = "def f():\n    return 1"
    tl = _build(script)
    typed = [s.typed for _, s in tl.keyframes if s.mode == EDITOR]
    assert typed[-1] == len(script)
    # Leading indentation appears at once after the newline
    assert script.index("return") in typed


def test_fit_scale_hits_target_duration():
    tl = _build("x = 1\n" * 40)
    scale = fit_scale(tl, 15, 1.0)
    fitted = _build("x = 1\n" * 40, pacing=Pacing(scale=scale))
    assert abs(fitted.duration - 15) < 1.5


def test_colorize_uses_theme_syntax_colors():
    script = "import os  # hi"
    colors = colorize(script, "a.py", THEME)
    assert colors[0] == THEME.syntax["Keyword"]
    assert colors[script.index("#")] == THEME.syntax["Comment"]


def test_parser_theme_list_matches_themes():
    from src.parser import REEL_THEMES

    assert REEL_THEMES == list(THEMES)


# ─────────────────────────── rendering ───────────────────────────
def test_preview_png(tmp_path):
    out = tmp_path / "frame.png"
    result = render_reel(
        ReelConfig(
            output=out,
            script="echo hi\n",
            title="Title",
            footer="@me",
            size=(360, 640),
            run=False,
            preview=True,
            seed=1,
        )
    )
    assert result.frames == 1
    from PIL import Image

    assert Image.open(out).size == (360, 640)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_render_small_video_with_audio(tmp_path):
    out = tmp_path / "reel.mp4"
    result = render_reel(
        ReelConfig(
            output=out,
            script="print('hello')\n",
            filename="hi.py",
            run_command=f"{sys.executable} hi.py",
            size=(270, 480),
            fps=10,
            pacing=Pacing(speed=0.01, variance=0.0, pause_probability=0),
            seed=1,
            preset="ultrafast",
        )
    )
    assert result.exit_code == 0
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(out)],
        text=True,
    ).split()  # fmt: skip
    assert probe == ["video", "audio"]


def test_c_files_compile_then_run():
    assert default_run_command("donut.c", "") == "gcc donut.c -o donut -lm && ./donut"


def test_full_screen_animation_shows_complete_frames_only():
    # Two frames, the second split across chunks; cursor-home starts each one
    chunks = [
        (0.0, "intro\n\x1b[2J"),
        (0.1, "\x1b[HAAA\nAAA\n"),
        (0.2, "\x1b[HBB"),
        (0.2001, "B\nBBB\n"),
        (0.3, "done\n"),
    ]
    tl = _build(chunks=chunks)
    screens = [
        ["".join(r[0] for r in line) for line in s.shell if line]
        for _, s in tl.keyframes
        if s.mode == SHELL
    ]
    assert ["AAA", "AAA"] in screens
    assert ["BBB", "BBB", "done"] in screens
    assert ["BB"] not in screens  # never a half-drawn frame


def test_title_wrap_is_balanced():
    from PIL import ImageFont

    from type_simulator.reel.render import _wrap_words, find_font

    font = ImageFont.truetype(find_font("sans:bold"), 66)
    lines = _wrap_words("A spinning 3D donut in pure C", font, 940)
    assert len(lines) == 2
    assert len(lines[-1].split()) > 1


def test_animation_text_after_a_pause_appears_progressively():
    chunks = [(0.0, "\x1b[2Jframe\n"), (0.5, "W"), (0.6, "a"), (0.7, "k")]
    tl = _build(chunks=chunks)
    texts = {
        "".join(r[0] for line in s.shell for r in line)
        for _, s in tl.keyframes
        if s.mode == SHELL
    }
    assert {"frameW", "frameWa", "frameWak"} <= texts


# ─────────────────────────── browser mode ───────────────────────────
def test_timeline_cuts_to_browser_frames():
    from type_simulator.reel.timeline import BROWSER

    builder = TimelineBuilder(THEME, Pacing(), rows=20, seed=3)
    tl = builder.build(
        "<h1>hi</h1>", "a.html", None, [], browser_command="firefox a.html",
        browser_frames=60, browser_fps=30,
    )  # fmt: skip
    browser = [(t, s) for t, s in tl.keyframes if s.mode == BROWSER]
    assert [s.frame for _, s in browser] == list(range(60))
    assert abs(tl.duration - (browser[0][0] + 2.0)) < 1e-6
    shell = [s for _, s in tl.keyframes if s.mode == SHELL][-1]
    assert "firefox a.html" in "".join(r[0] for line in shell.shell for r in line)


def test_renderer_composites_page_frames(tmp_path):
    from PIL import Image

    from type_simulator.reel.browser import PageCapture
    from type_simulator.reel.render import (
        FrameRenderer,
        browser_viewport,
        compute_layout,
        find_font,
    )
    from type_simulator.reel.timeline import BROWSER, Scene

    layout = compute_layout(540, 960, None, find_font("monospace"))
    x0, y0, x1, y1 = browser_viewport(layout)
    capture = PageCapture(tmp_path, 2, 30, (x1 - x0, y1 - y0), title="Page")
    for i, color in enumerate([(255, 0, 0), (0, 0, 255)]):
        Image.new("RGB", capture.size, color).save(capture.path(i))
    renderer = FrameRenderer(
        THEME, layout, "x", [None], "a.html", capture=capture, url="file:///a.html"
    )
    center = ((x0 + x1) // 2, (y0 + y1) // 2)
    first = renderer.render(Scene(BROWSER, frame=0), False)
    second = renderer.render(Scene(BROWSER, frame=1), False)
    assert first.getpixel(center)[0] > 240
    assert second.getpixel(center)[2] > 240
    # Rounded window corners stay intact, so the page doesn't spill over
    assert first.getpixel((x0, y1 - 1)) != first.getpixel(center)


def test_validation_requires_playwright_for_browser_reels(monkeypatch):
    from type_simulator.reel import browser
    from type_simulator.validation import validate_inputs

    monkeypatch.setattr(browser, "playwright_available", lambda: False)
    ok, errors, _ = validate_inputs("reel", "out.mp4", None, "<p>", browser=True)
    assert not ok and any("Playwright" in e for e in errors)


def test_cli_picks_browser_by_extension():
    from types import SimpleNamespace

    from src.main import _reel_uses_browser

    args = SimpleNamespace(browser=None, filename=None, input="site/index.HTML")
    assert _reel_uses_browser(args)
    assert not _reel_uses_browser(
        SimpleNamespace(browser=None, filename=None, input="a.py")
    )
    assert not _reel_uses_browser(
        SimpleNamespace(browser=False, filename=None, input="a.html")
    )


def _chromium_works():
    from type_simulator.reel.browser import playwright_available

    if not playwright_available():
        return False
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _chromium_works(), reason="Playwright Chromium not available")
def test_capture_page_advances_animation_frame_by_frame(tmp_path):
    from PIL import ImageChops

    from type_simulator.reel.browser import capture_page

    page = tmp_path / "anim.html"
    page.write_text(
        "<title>Anim</title><body style=margin:0><canvas id=c></canvas><script>"
        "const c=document.getElementById('c'),x=c.getContext('2d');"
        "c.width=innerWidth;c.height=innerHeight;"
        "requestAnimationFrame(function f(t){x.fillStyle='#000';"
        "x.fillRect(0,0,c.width,c.height);x.fillStyle='#fff';"
        "x.fillRect(t/10,0,20,20);requestAnimationFrame(f)})</script>"
    )
    capture = capture_page(page, (200, 120), 10, 0.5, tmp_path / "frames")
    assert capture.count == 5
    assert capture.title == "Anim"
    assert capture.console_errors == []
    frames = [capture.frame(i) for i in range(5)]
    assert all(f.size == (200, 120) for f in frames)
    # The square moves 10 px per 100 ms frame
    assert ImageChops.difference(frames[0], frames[1]).getbbox() is not None
