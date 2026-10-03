"""Color themes for rendered reels."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

RGB = Tuple[int, int, int]


def _hex(value: str) -> RGB:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


@dataclass(frozen=True)
class Theme:
    name: str
    bg_top: RGB
    bg_bottom: RGB
    window_bg: RGB
    titlebar_bg: RGB
    titlebar_fg: RGB
    fg: RGB
    dim: RGB
    accent: RGB
    path: RGB
    title_fg: RGB
    subtitle_fg: RGB
    # 16 ANSI colors: black, red, green, yellow, blue, magenta, cyan, white,
    # then the bright variants in the same order
    ansi: List[RGB]
    # Pygments token type name (e.g. "Keyword", "Name.Function") -> color
    syntax: Dict[str, RGB] = field(default_factory=dict)
    prompt: str = "dev@reel"
    scanlines: bool = False


def _theme(name: str, **colors) -> Theme:
    syntax = {k: _hex(v) for k, v in colors.pop("syntax").items()}
    ansi = [_hex(c) for c in colors.pop("ansi")]
    plain = {
        k: (_hex(v) if isinstance(v, str) and v.startswith("#") else v)
        for k, v in colors.items()
    }
    return Theme(name=name, ansi=ansi, syntax=syntax, **plain)


THEMES: Dict[str, Theme] = {
    "hacker": _theme(
        "hacker",
        bg_top="#03140a",
        bg_bottom="#000000",
        window_bg="#020a05",
        titlebar_bg="#0a1f12",
        titlebar_fg="#5dbb7a",
        fg="#39ff7a",
        dim="#1e6b3a",
        accent="#39ff7a",
        path="#00e5ff",
        title_fg="#39ff7a",
        subtitle_fg="#8affb0",
        prompt="root@kali",
        scanlines=True,
        ansi=[
            "#0b2414",
            "#ff4f5e",
            "#39ff7a",
            "#e8ff5a",
            "#3fa9ff",
            "#d070ff",
            "#00e5ff",
            "#c8ffd8",
            "#2e5c3d",
            "#ff7b86",
            "#7dffa6",
            "#f4ff9a",
            "#7cc6ff",
            "#e3a3ff",
            "#7ff3ff",
            "#ffffff",
        ],
        syntax={
            "Keyword": "#b6ff4d",
            "Name.Builtin": "#00e5ff",
            "Name.Function": "#e8ff5a",
            "Name.Class": "#e8ff5a",
            "Name.Decorator": "#00e5ff",
            "String": "#7dffa6",
            "Number": "#00ffcc",
            "Comment": "#1f8a45",
            "Operator": "#b6ff4d",
            "Name.Variable": "#8affb0",
        },
    ),
    "dracula": _theme(
        "dracula",
        bg_top="#3b2a5c",
        bg_bottom="#14121f",
        window_bg="#282a36",
        titlebar_bg="#1f2029",
        titlebar_fg="#a7abc4",
        fg="#f8f8f2",
        dim="#6272a4",
        accent="#50fa7b",
        path="#bd93f9",
        title_fg="#ffffff",
        subtitle_fg="#ff79c6",
        ansi=[
            "#21222c",
            "#ff5555",
            "#50fa7b",
            "#f1fa8c",
            "#bd93f9",
            "#ff79c6",
            "#8be9fd",
            "#f8f8f2",
            "#6272a4",
            "#ff6e6e",
            "#69ff94",
            "#ffffa5",
            "#d6acff",
            "#ff92df",
            "#a4ffff",
            "#ffffff",
        ],
        syntax={
            "Keyword": "#ff79c6",
            "Name.Builtin": "#8be9fd",
            "Name.Function": "#50fa7b",
            "Name.Class": "#8be9fd",
            "Name.Decorator": "#50fa7b",
            "String": "#f1fa8c",
            "Number": "#bd93f9",
            "Comment": "#6272a4",
            "Operator": "#ff79c6",
            "Name.Variable": "#f8f8f2",
        },
    ),
    "monokai": _theme(
        "monokai",
        bg_top="#3a2f12",
        bg_bottom="#111111",
        window_bg="#272822",
        titlebar_bg="#1e1f1a",
        titlebar_fg="#a59f85",
        fg="#f8f8f2",
        dim="#75715e",
        accent="#a6e22e",
        path="#66d9ef",
        title_fg="#ffffff",
        subtitle_fg="#e6db74",
        ansi=[
            "#272822",
            "#f92672",
            "#a6e22e",
            "#f4bf75",
            "#66d9ef",
            "#ae81ff",
            "#a1efe4",
            "#f8f8f2",
            "#75715e",
            "#ff4f8b",
            "#c1f05c",
            "#ffd68f",
            "#8fe6f7",
            "#c9a7ff",
            "#c2f7ef",
            "#ffffff",
        ],
        syntax={
            "Keyword": "#f92672",
            "Name.Builtin": "#66d9ef",
            "Name.Function": "#a6e22e",
            "Name.Class": "#a6e22e",
            "Name.Decorator": "#a6e22e",
            "String": "#e6db74",
            "Number": "#ae81ff",
            "Comment": "#75715e",
            "Operator": "#f92672",
            "Name.Variable": "#f8f8f2",
        },
    ),
    "nord": _theme(
        "nord",
        bg_top="#3b4a66",
        bg_bottom="#191d26",
        window_bg="#2e3440",
        titlebar_bg="#252a34",
        titlebar_fg="#9aa5b8",
        fg="#d8dee9",
        dim="#616e88",
        accent="#88c0d0",
        path="#81a1c1",
        title_fg="#eceff4",
        subtitle_fg="#88c0d0",
        ansi=[
            "#3b4252",
            "#bf616a",
            "#a3be8c",
            "#ebcb8b",
            "#81a1c1",
            "#b48ead",
            "#88c0d0",
            "#e5e9f0",
            "#4c566a",
            "#d08770",
            "#b5d19c",
            "#f0d9a6",
            "#9ab6d6",
            "#c7a6c1",
            "#8fbcbb",
            "#eceff4",
        ],
        syntax={
            "Keyword": "#81a1c1",
            "Name.Builtin": "#88c0d0",
            "Name.Function": "#88c0d0",
            "Name.Class": "#8fbcbb",
            "Name.Decorator": "#d08770",
            "String": "#a3be8c",
            "Number": "#b48ead",
            "Comment": "#616e88",
            "Operator": "#81a1c1",
            "Name.Variable": "#d8dee9",
        },
    ),
}

DEFAULT_THEME = "hacker"


def get_theme(name: str) -> Theme:
    try:
        return THEMES[name]
    except KeyError:
        raise ValueError(
            f"Unknown theme '{name}'. Available: {', '.join(THEMES)}"
        ) from None
