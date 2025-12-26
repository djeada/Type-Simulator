# Type-Simulator

**Type-Simulator** is a versatile Python tool for automating human-like typing in any text editor or input field. Whether you’re creating demos, running automated tutorials, or stress‑testing text‑based applications, Type‑Simulator lets you control keyboard inputs with precision and randomness for a natural effect.

## 🚀 Features

- **Human-Like Typing**: Configurable speed and variance simulate real typing habits.
- **Typing Profiles**: Pre-built profiles (human, fast, slow, robotic, hunt-and-peck) for different scenarios.
- **Editor Agnostic**: Launch any GUI or terminal-based editor via customizable commands (default: `xterm -e vi`).
- **Flexible Input**: Type directly passed text or contents of a file.
- **Advanced Control**: Supports special keys (Esc, Enter, arrows) and complex keystroke sequences.
- **Macro Commands**: Powerful macro syntax for automation:
  - `{REPEAT_N}...{/REPEAT}` - Repeat blocks of content N times
  - `{RANDOM_N}` - Generate random text of N characters
  - `{SPEED_X}` - Change typing speed dynamically
  - `{SET_var=value}` / `{GET_var}` - Variables for dynamic content
  - `{WAIT_N}` - Pause for N seconds
  - Mouse actions, key combinations, and more
- **Extensible Modes**:
  - **GUI**: Drive a full editor (e.g. vim, gedit) under Xvfb for headless CI.
  - **Terminal**: Open a terminal emulator for shell-driven typing.
  - **Direct**: Write text straight to a file without a GUI.
  - **Focus**: Type directly into the currently focused window (requires platform-specific tools).
- **Statistics**: Get detailed typing statistics with `--stats` flag.
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
# Basic direct mode
python -m src.main --mode direct --output demo.txt --input "Hello, World!"

# Use a typing profile for natural typing
python -m src.main --mode focus --input "Natural typing" --profile human

# Fast typing profile
python -m src.main --mode focus --input "Speed typing" --profile fast

# Terminal mode
python -m src.main --mode terminal --input "ls -la"

# Direct mode with custom speed
python -m src.main --mode direct --output file.txt --input "Quick write" --speed 0.05

# Platform-agnostic focus mode
python -m src.main --mode focus --input "Platform-agnostic typing"

# Input from file
python -m src.main --mode direct --output demo.txt --input demo_macro.txt

# Pipe mode (STDIN, requires --output in direct mode)
cat demo_macro.txt | python -m src.main --mode direct --output demo.txt

# Show statistics after typing
python -m src.main --mode direct --output demo.txt --input "Test text" --stats

# List available typing profiles
python -m src.main --list-profiles
```

### Macro Commands

Type-Simulator supports powerful macro commands for automation:

```sh
# Repeat a block 3 times
python -m src.main --mode focus --input "{REPEAT_3}Hello {/REPEAT}"
# Output: Hello Hello Hello 

# Generate random text
python -m src.main --mode focus --input "Password: {RANDOM_12}"
# Output: Password: aB3xK9pLmN2q

# Change typing speed mid-text
python -m src.main --mode focus --input "{SPEED_0.1}Slow start{SPEED_0.02}Fast finish"

# Use variables
python -m src.main --mode focus --input "{SET_name=World}Hello, {GET_name}!"
# Output: Hello, World!

# Wait between actions
python -m src.main --mode focus --input "Step 1{WAIT_2}Step 2"

# Key combinations
python -m src.main --mode focus --input "Select all: {<ctrl>+a}"

# Mouse actions
python -m src.main --mode focus --input "{MOUSE_MOVE_500_300}{MOUSE_CLICK_left}"
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
