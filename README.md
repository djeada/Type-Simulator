# Type-Simulator

**Type-Simulator** is a versatile Python tool for automating human-like typing in any text editor or input field. Whether you’re creating demos, running automated tutorials, or stress‑testing text‑based applications, Type‑Simulator lets you control keyboard inputs with precision and randomness for a natural effect.

## 🚀 Features

- **Human-Like Typing**: Configurable speed and variance simulate real typing habits.
- **Editor Agnostic**: Launch any GUI or terminal-based editor via customizable commands (default: `xterm -e vi`).
- **Flexible Input**: Type directly passed text or contents of a file.
- **Advanced Control**: Supports special keys (Esc, Enter, arrows) and complex keystroke sequences.
- **Extensible Modes**:
  - **GUI**: Drive a full editor (e.g. vim, gedit) under Xvfb for headless CI.
  - **Terminal**: Open a terminal emulator for shell-driven typing.
  - **Direct**: Write text straight to a file without a GUI.
  - **Focus**: Type directly into the currently focused window (requires platform-specific tools).
- **Verbose Logging**: Adjustable log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`) for troubleshooting.

## 📦 Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/djeada/Type-Simulator.git
   cd Type-Simulator
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

> **Tip:** For CI pipelines, install system packages:
> ```bash
> sudo apt-get update && sudo apt-get install -y xvfb xterm xdotool xfonts-base
> ```

## 🏗️ Build & Distribution

We provide build scripts powered by [Nuitka](https://nuitka.net/) to compile the Python code into standalone executables. These scripts can generate cross-platform binaries (Linux, Windows, macOS) and are maintained in the `build/` directory. On each major release, we publish pre‑built Linux x86 executables under `releases/`, so you can run Type‑Simulator without installing Python or dependencies.

```bash
# Build a Linux x86 executable locally:
cd build
./build_linux_x86.sh
# Result: dist/type_simulator (standalone binary)
```

You can also customize the build by editing `build/config.json` to target different platforms or include additional modules.

## 💻 Usage

Run via Python module interface:

```bash
# Basic mode with file output (direct mode)
python -m src.main \
  --output <path/to/output.txt> \  # destination file (only for direct mode)
  --input "Your text here"   # input: file path or literal text
  --mode direct \
  --speed 0.1 \                # seconds/char (default: 0.15)
  --variance 0.02 \            # typing variance (default: 0.05)
  --log-level DEBUG            # log verbosity (optional)
```

### Examples

```sh
python -m src.main --mode direct --output demo.txt --input "Hello, World!"

python -m src.main --mode terminal --input "ls -la"

python -m src.main --mode direct --output file.txt --input "Quick write"

python -m src.main --mode focus --input "Platform-agnostic typing"

# Input from file
python -m src.main --mode direct --output demo.txt --input demo_macro.txt

# Pipe mode (STDIN, requires --output in direct mode)
cat demo_macro.txt | python -m src.main --mode direct --output demo.txt
```

**Note:**
- The `--input` flag accepts either a file path or literal text. If the value is a valid file path, its contents will be used; otherwise, the value is treated as literal text.
- If `--input` is omitted, input will be read from STDIN (pipe mode). In direct mode, `--output` is required.

## 🔧 Customization

- **Add Special Keys**: Extend `src/type_simulator/text_typer.py` to handle additional key sequences.
- **New Editors**: Override the default `xterm` command in your calls or via `--editor-script`.
- **CI Integration**: Use `tests/run_tests.sh` wrapper and GitHub Actions snippets in `.github/workflows` for automated E2E tests.

## 📝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Submit a pull request with tests and documentation

## 📜 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
