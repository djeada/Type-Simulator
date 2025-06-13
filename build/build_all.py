#!/usr/bin/env python3
import argparse
import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path

BIN_NAME = "type_simulator"
ASSUME_YES = "--assume-yes-for-downloads"

SUPPORTED_PLATFORMS = {
    "linux":   {"args": ["--onefile"],                         "suffix": "_linux"},
    "darwin":  {"args": ["--macos-create-app-bundle"],         "suffix": "_macos", "archive": True},
    "windows": {"args": ["--onefile"],                         "suffix": "_windows.exe"},
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def detect_platform() -> str:
    s = platform.system().lower()
    if s.startswith("linux"):
        return "linux"
    if s.startswith("darwin"):
        return "darwin"
    if s.startswith("windows"):
        return "windows"
    raise RuntimeError(f"Unsupported platform: {platform.system()}")


def find_nuitka() -> Path:
    for name in ("nuitka", "nuitka3", "nuitka.exe"):
        which = shutil.which(name)
        if which:
            return Path(which)
    raise RuntimeError("Nuitka not found. Install with: pip install -r requirements-dev.txt")


def clean_dist(dist_dir: Path) -> None:
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True)


def build_with_nuitka(nuitka: Path, src: Path, dist_dir: Path, extra: list[str]) -> None:
    cmd = [
        str(nuitka),
        "--standalone",
        ASSUME_YES,
        *extra,
        f"--output-dir={dist_dir}",
        str(src)
    ]
    logging.info("Running build command:\n    %s", " ".join(cmd))
    subprocess.check_call(cmd)


def collect_artifacts(dist_dir: Path, bin_name: str, platform_key: str, project_root: Path) -> list[Path]:
    info = SUPPORTED_PLATFORMS[platform_key]
    suffix = info["suffix"]
    artifacts: list[Path] = []

    if platform_key in ("linux", "windows"):
        exe = next(dist_dir.glob("main*"))
        target = dist_dir / f"{bin_name}{suffix}"
        exe.rename(target)
        artifacts.append(target)

    else:  # darwin
        app = next(dist_dir.glob("*.app"))
        renamed = dist_dir / f"{bin_name}{suffix}.app"
        app.rename(renamed)

        if info.get("archive"):
            zip_path = dist_dir / f"{bin_name}{suffix}.zip"
            shutil.make_archive(
                str(zip_path.with_suffix('')), 'zip',
                root_dir=dist_dir, base_dir=renamed.name
            )
            logging.info("Created archive: %s", zip_path)
            artifacts.append(zip_path)
            shutil.rmtree(renamed)
        else:
            artifacts.append(renamed)

    logging.info("Collected artifacts: %s", artifacts)
    return artifacts


def prune_dist(dist_dir: Path, keep: list[Path]) -> None:
    for item in dist_dir.iterdir():
        if item not in keep:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


def clean_root_artifacts(project_root: Path) -> None:
    # Remove any file not starting with BIN_NAME + '_'
    for f in project_root.iterdir():
        if f.is_file() and not f.name.startswith(f"{BIN_NAME}_"):
            try:
                f.unlink()
                logging.info("Removed root artifact: %s", f)
            except Exception:
                pass


def verify_dist(dist_dir: Path, expected: int) -> None:
    remaining = list(dist_dir.iterdir())
    if len(remaining) != expected:
        logging.error("Unexpected files left in %s: %s", dist_dir, remaining)
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Build standalone binary with Nuitka")
    p.add_argument("--src",      type=Path, default=Path(__file__).parent.parent / "src" / "main.py")
    p.add_argument("--dist",     type=Path, default=Path(__file__).parent.parent / "dist")
    p.add_argument("--bin-name", default=BIN_NAME)
    return p.parse_args()


def main():
    args = parse_args()
    project_root = args.src.parent.parent
    plat = detect_platform()
    logging.info("=== Building for %s ===", plat.capitalize())

    clean_dist(args.dist)
    nuitka = find_nuitka()
    extra_args = SUPPORTED_PLATFORMS[plat]["args"]

    build_with_nuitka(nuitka, args.src, args.dist, extra_args)
    artifacts = collect_artifacts(args.dist, args.bin_name, plat, project_root)

    prune_dist(args.dist, artifacts)
    clean_root_artifacts(project_root)
    verify_dist(args.dist, expected=len(artifacts))

    logging.info("%s build complete!", plat.capitalize())


if __name__ == "__main__":
    main()
