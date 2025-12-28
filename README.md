# Type-Simulator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-green)](https://github.com/djeada/Type-Simulator)

**Type-Simulator** is a versatile Python tool for automating human-like typing in any text editor or input field. Whether you're creating demos, running automated tutorials, or stress-testing text-based applications, Type-Simulator lets you control keyboard inputs with precision and randomness for a natural effect.

## 📑 Table of Contents

- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
  - [Basic Examples](#basic-examples)
  - [Command Line Options](#command-line-options)
- [Typing Modes](#-typing-modes)
- [Typing Profiles](#-typing-profiles)
- [Macro Commands](#-macro-commands)
  - [Text Control Macros](#text-control-macros)
  - [Timing Macros](#timing-macros)
  - [Mouse Control Macros](#mouse-control-macros)
  - [Keyboard Macros](#keyboard-macros)
  - [Variable Macros](#variable-macros)
- [Build & Distribution](#-build--distribution)
- [Advanced Usage](#-advanced-usage)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Features

- **Human-Like Typing**: Configurable speed and variance simulate real typing habits
- **Typing Profiles**: Pre-built profiles (human, fast, slow, robotic, hunt-and-peck) for different scenarios
- **Editor Agnostic**: Works with any text editor or input field
- **Flexible Input**: Accept text from command line, files, or STDIN
- **Multiple Modes**: 
  - **GUI Mode**: Drive a full editor (e.g., vim, gedit) under Xvfb for headless CI
  - **Terminal Mode**: Open a terminal emulator for shell-driven typing
  - **Direct Mode**: Write text straight to a file without a GUI
  - **Focus Mode**: Type directly into the currently focused window
- **Powerful Macro System**: Support for repeat blocks, random text, speed changes, variables, waits, mouse actions, and key combinations
- **Statistics**: Get detailed typing statistics including WPM, characters per second, and duration
- **Dry Run**: Validate input without executing actions
- **Verbose Logging**: Adjustable log levels (DEBUG, INFO, WARNING, ERROR) for troubleshooting

## 🖥️ System Requirements

- **Python**: 3.7 or higher
- **Operating System**: Linux, macOS, or Windows
- **For GUI/Terminal modes on Linux**: 
  - `xvfb` - Virtual framebuffer for headless operation
  - `xterm` - Terminal emulator (default)
  - `xdotool` - X11 automation tool
  - `xfonts-base` - Basic X11 fonts

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/djeada/Type-Simulator.git
cd Type-Simulator
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies include:**
- PyAutoGUI - Cross-platform GUI automation
- python3-xlib - Python X11 library
- Pillow - Python Imaging Library
- pyperclip - Clipboard access

### 3. Install System Packages (Linux)

For GUI and terminal modes on Linux, install these system packages:

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y xvfb xterm xdotool xfonts-base

# Fedora/RHEL
sudo dnf install -y xorg-x11-server-Xvfb xterm xdotool xorg-x11-fonts-misc

# Arch Linux
sudo pacman -S xorg-server-xvfb xterm xdotool xorg-fonts-misc
```

## ⚡ Quick Start

Here's the simplest way to get started:

```bash
# Write "Hello, World!" to a file
python -m src.main --mode direct --output hello.txt --input "Hello, World!"

# Type into the currently focused window
python -m src.main --mode focus --input "This text will be typed!"

# Use a typing profile for natural typing
python -m src.main --mode focus --input "Natural typing" --profile human

# Type content from a file
python -m src.main --mode direct --output result.txt --input demo/demo_type_text.txt
```

## 💻 Usage

### Basic Examples

```bash
# Direct mode - Write to file with custom speed
python -m src.main --mode direct --output demo.txt --input "Hello, World!" --speed 0.1

# Focus mode - Type into active window with a profile
python -m src.main --mode focus --input "Fast typing demo" --profile fast

# Terminal mode - Execute shell commands
python -m src.main --mode terminal --input "ls -la"

# GUI mode - Open an editor and type
python -m src.main --mode gui --editor-script "gedit" --input "Text in gedit"

# Read from STDIN (pipe mode)
echo "Piped text" | python -m src.main --mode direct --output output.txt

# Show statistics after typing
python -m src.main --mode direct --output demo.txt --input "Test text" --stats

# Dry run - Validate without executing
python -m src.main --mode direct --output demo.txt --input "{REPEAT_3}Test{/REPEAT}" --dry-run

# List available profiles
python -m src.main --list-profiles
```

### Command Line Options

```
usage: type_simulator [-h] [-e EDITOR_SCRIPT] [--mode {gui,terminal,direct,focus}]
                      [-s SPEED] [-v VARIANCE] [-p PROFILE] [-i INPUT] [-o OUTPUT]
                      [--log-level {DEBUG,INFO,WARNING,ERROR}] [-w WAIT]
                      [--pre-launch-cmd CMD] [-V] [--dry-run] [--stats]
                      [--list-profiles]

Options:
  -h, --help            Show help message and exit
  -e, --editor-script   Command to open the editor (default: 'xterm -e vi')
  --mode                Typing mode: gui, terminal, direct, or focus
  -s, --speed           Typing speed in seconds per character
  -v, --variance        Random variation in typing speed
  -p, --profile         Use a preset typing profile
  -i, --input           Input text or file path to type
  -o, --output          Output file path (required for direct mode)
  --log-level           Logging verbosity (default: INFO)
  -w, --wait            Seconds to wait after typing before closing
  --pre-launch-cmd      Command to run before typing starts
  -V, --version         Show version and exit
  --dry-run             Validate input without executing
  --stats               Show typing statistics after completion
  --list-profiles       List available typing profiles
```

## 🎯 Typing Modes

Type-Simulator supports four different typing modes:

### 1. Direct Mode (`--mode direct`)

Writes text directly to a file without any GUI interaction. Fastest mode, ideal for generating text files.

**Required:** `--output` flag to specify destination file

```bash
python -m src.main --mode direct --output result.txt --input "Direct write"
```

### 2. Focus Mode (`--mode focus`)

Types into the currently focused window using platform-specific automation tools. Works across different applications and platforms.

**Best for:** Live demos, presentations, automated data entry

```bash
python -m src.main --mode focus --input "Types into active window"
```

### 3. Terminal Mode (`--mode terminal`)

Opens a terminal emulator and types the input as shell commands. Useful for automating command-line operations.

**Best for:** Shell command demonstrations, CLI tutorials

```bash
python -m src.main --mode terminal --input "echo 'Hello from terminal!'"
```

### 4. GUI Mode (`--mode gui`)

Launches a full text editor and types into it. Can run headlessly using Xvfb for CI/CD pipelines.

**Best for:** Editor-specific demonstrations, vim tutorials, headless CI testing

```bash
python -m src.main --mode gui --editor-script "gedit" --input "Text in editor"
python -m src.main --mode gui --editor-script "xterm -e vim" --input "Vim commands"
```

## 🎹 Typing Profiles

Type-Simulator includes pre-configured typing profiles that simulate different typing styles:

| Profile | Speed | Variance | Description |
|---------|-------|----------|-------------|
| `human` | 0.08s | 0.04 | Natural human typing with realistic variations |
| `fast` | 0.03s | 0.01 | Quick professional typing |
| `slow` | 0.2s | 0.08 | Careful, deliberate typing |
| `robotic` | 0.05s | 0.0 | Mechanical, consistent typing with no variance |
| `hunt_and_peck` | 0.4s | 0.2 | Slow, searching for keys typing style |

**Usage:**

```bash
# Use a profile
python -m src.main --mode focus --input "Natural typing" --profile human

# Override profile settings with custom speed/variance
python -m src.main --mode focus --input "Custom" --profile human --speed 0.05 --variance 0.02

# List all available profiles
python -m src.main --list-profiles
```

## 🔧 Macro Commands

Type-Simulator supports a powerful macro system for advanced automation. Macros are enclosed in curly braces `{}`.

### Text Control Macros

#### Repeat Blocks
Repeat a block of text multiple times.

**Syntax:** `{REPEAT_N}...text...{/REPEAT}`

```bash
# Output: "Hello Hello Hello "
python -m src.main --mode focus --input "{REPEAT_3}Hello {/REPEAT}"

# Nested example
python -m src.main --mode focus --input "{REPEAT_2}Line {REPEAT_3}* {/REPEAT}{/REPEAT}"
# Output: "Line * * * Line * * * "
```

#### Random Text Generation
Generate random text of specified length.

**Syntax:** `{RANDOM_length}` or `{RANDOM_length_charset}`

**Charsets:** `alphanumeric`, `alpha`, `numeric`, `custom:ABC123`

```bash
# Generate 12 random alphanumeric characters
python -m src.main --mode focus --input "Password: {RANDOM_12}"

# Generate 8 random letters
python -m src.main --mode focus --input "Code: {RANDOM_8_alpha}"

# Generate 6 random numbers
python -m src.main --mode focus --input "PIN: {RANDOM_6_numeric}"

# Custom character set
python -m src.main --mode focus --input "Hex: {RANDOM_16_custom:0123456789ABCDEF}"
```

### Timing Macros

#### Wait/Pause
Pause typing for a specified number of seconds.

**Syntax:** `{WAIT_seconds}`

```bash
# Wait 2 seconds between actions
python -m src.main --mode focus --input "Step 1{WAIT_2}Step 2{WAIT_1.5}Step 3"

# Wait before typing starts
python -m src.main --mode focus --input "{WAIT_1}Started after 1 second"
```

#### Speed Changes
Change typing speed dynamically during execution.

**Syntax:** `{SPEED_speed}` or `{SPEED_speed_variance}`

```bash
# Change speed mid-text
python -m src.main --mode focus --input "{SPEED_0.2}Slow start{SPEED_0.02}Fast finish"

# Speed with variance
python -m src.main --mode focus --input "{SPEED_0.1_0.05}Variable speed typing"
```

### Mouse Control Macros

#### Mouse Movement
Move mouse cursor to specific coordinates.

**Syntax:** `{MOUSE_MOVE_x_y}`

```bash
# Move mouse to position (500, 300)
python -m src.main --mode focus --input "{MOUSE_MOVE_500_300}"

# Move and click
python -m src.main --mode focus --input "{MOUSE_MOVE_100_200}{WAIT_0.2}{MOUSE_CLICK_left}"
```

#### Mouse Clicks
Click mouse buttons at current position.

**Syntax:** `{MOUSE_CLICK_button}`

**Buttons:** `left`, `right`, `middle`

```bash
# Left click
python -m src.main --mode focus --input "{MOUSE_CLICK_left}"

# Right click for context menu
python -m src.main --mode focus --input "{MOUSE_CLICK_right}"

# Double-click
python -m src.main --mode focus --input "{MOUSE_CLICK_left}{MOUSE_CLICK_left}"

# Complete mouse workflow
python -m src.main --mode focus --input "{MOUSE_MOVE_500_300}{WAIT_0.5}{MOUSE_CLICK_right}{WAIT_0.3}{MOUSE_CLICK_left}"
```

### Keyboard Macros

#### Special Keys and Combinations
Simulate keyboard shortcuts and special keys.

**Syntax:** `{<key>}` or `{<modifier>+<key>}`

**Common Keys:** `enter`, `esc`, `tab`, `backspace`, `delete`, `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`

**Modifiers:** `ctrl`, `alt`, `shift`, `win`/`cmd`

```bash
# Press Enter
python -m src.main --mode focus --input "Hello{<enter>}World"

# Keyboard shortcuts
python -m src.main --mode focus --input "{<ctrl>+a}"  # Select all
python -m src.main --mode focus --input "{<ctrl>+c}"  # Copy
python -m src.main --mode focus --input "{<ctrl>+v}"  # Paste
python -m src.main --mode focus --input "{<ctrl>+s}"  # Save

# Multiple modifiers
python -m src.main --mode focus --input "{<ctrl>+<shift>+n}"  # Ctrl+Shift+N

# Navigation
python -m src.main --mode focus --input "{<home>}Start of line{<end>}"
python -m src.main --mode focus --input "{<up>}{<up>}{<down>}"

# Windows/Mac key
python -m src.main --mode focus --input "{<win>+r}"  # Open Run dialog (Windows)
python -m src.main --mode focus --input "{<cmd>+space}"  # Spotlight (Mac)
```

#### Complex Shortcuts Example

```bash
# Complete workflow: Open Run, launch cmd, execute command
python -m src.main --mode focus --input "{<win>+r}{WAIT_0.3}cmd{<enter>}{WAIT_1}echo Demo{<enter>}"
```

### Variable Macros

Store and retrieve values during execution.

**Syntax:** 
- Set: `{SET_name=value}`
- Get: `{GET_name}`

```bash
# Set and use a variable
python -m src.main --mode focus --input "{SET_name=World}Hello, {GET_name}!"
# Output: "Hello, World!"

# Multiple variables
python -m src.main --mode focus --input "{SET_user=Alice}{SET_action=logged in}{GET_user} has {GET_action}"
# Output: "Alice has logged in"

# Variables with repeats
python -m src.main --mode focus --input "{SET_msg=Hello }{REPEAT_3}{GET_msg}{/REPEAT}"
# Output: "Hello Hello Hello "
```

### Literal Braces

To type literal curly braces, escape them with backslash:

```bash
# Output: "{literal braces}"
python -m src.main --mode focus --input "\{literal braces\}"

# Output: "Function: void func() {}"
python -m src.main --mode focus --input "Function: void func() \{\}"
```

### Complete Macro Example

Combining multiple macro types:

```bash
python -m src.main --mode focus --input "
{SET_username=admin}
{WAIT_0.5}
{SPEED_0.1}
Username: {GET_username}{<enter>}
{WAIT_0.3}
{SPEED_0.15}
Password: {RANDOM_12}{<enter>}
{WAIT_1}
{MOUSE_MOVE_500_300}
{MOUSE_CLICK_left}
{WAIT_0.5}
{REPEAT_3}Processing{WAIT_0.5}{<backspace>+{WAIT_0.3}{/REPEAT}
Done!"
```

## 🏗️ Build & Distribution

Type-Simulator can be compiled into standalone executables using [Nuitka](https://nuitka.net/). This allows distribution without requiring Python or dependencies to be installed.

### Building with Nuitka

#### Linux Build

```bash
# Install Nuitka (if not already installed)
pip install -r requirements-dev.txt

# Build using the provided script
cd build
./build_linux_x86.sh

# Result: dist/type_simulator (standalone executable)
```

The build script will:
1. Auto-detect the project structure
2. Compile `src/main.py` using Nuitka
3. Create a standalone, single-file executable in `dist/`

#### Manual Build

You can also build manually with custom Nuitka options:

```bash
# Standalone build
nuitka --standalone --onefile \
  --output-dir=dist \
  --output-filename=type_simulator \
  src/main.py

# With optimizations
nuitka --standalone --onefile \
  --follow-imports \
  --enable-plugin=pylint-warnings \
  --output-dir=dist \
  --output-filename=type_simulator \
  src/main.py
```

### Build Scripts

The `build/` directory contains build automation:

- `build_linux_x86.sh` - Build for Linux x86/x64
- `build_all.py` - Cross-platform build automation (experimental)

### Distribution

After building, the `dist/type_simulator` executable can be:
- Run directly without Python installation
- Distributed as a single file
- Used in CI/CD pipelines without dependency installation

```bash
# Run the built executable
./dist/type_simulator --mode focus --input "Hello from executable!" --profile human
```

**Note:** GitHub Releases may include pre-built executables for major versions. Check the [Releases page](https://github.com/djeada/Type-Simulator/releases) for available downloads.

## 🔬 Advanced Usage

### CI/CD Integration

Type-Simulator works great in headless CI environments:

```yaml
# GitHub Actions example
name: Demo Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y xvfb xterm xdotool xfonts-base
          pip install -r requirements.txt
      
      - name: Run typing demo
        run: |
          xvfb-run python -m src.main --mode gui --input "CI Demo" --stats
```

### Pre-Launch Commands

Execute commands before typing starts:

```bash
# Start a screen recorder before typing
python -m src.main --mode focus --input "Recording this" \
  --pre-launch-cmd "recordmydesktop --on-the-fly-encoding -o demo.ogv"

# Set up environment
python -m src.main --mode terminal --input "echo 'Test'" \
  --pre-launch-cmd "export TEST_VAR=value"
```

### Custom Editor Scripts

Use any editor or application:

```bash
# Use VS Code
python -m src.main --mode gui --editor-script "code" --input "VS Code text"

# Use nano
python -m src.main --mode gui --editor-script "xterm -e nano" --input "Nano text"

# Use emacs
python -m src.main --mode gui --editor-script "emacs" --input "Emacs text"

# Custom terminal
python -m src.main --mode terminal --editor-script "gnome-terminal --" --input "ls -la"
```

### Reading from Files

The `--input` flag accepts both literal text and file paths:

```bash
# Type contents of a file
python -m src.main --mode focus --input demo/demo_macro.txt

# If the file doesn't exist, treats as literal text
python -m src.main --mode focus --input "This is literal text, not a file"
```

### Long-Running Demos

Keep the editor open after typing:

```bash
# Wait 10 seconds before closing
python -m src.main --mode gui --input "Demo text" --wait 10

# Keep open indefinitely (use Ctrl+C to close)
python -m src.main --mode gui --input "Demo text" --wait 9999
```

## 🐛 Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'pyautogui'"

**Solution:** Install Python dependencies:
```bash
pip install -r requirements.txt
```

Note: The package name is case-sensitive - it's `PyAutoGUI` in requirements.txt but imports as `pyautogui`.

#### "Command 'xdotool' not found" or "xterm: command not found"

**Solution:** Install system packages (Linux):
```bash
sudo apt-get install xvfb xterm xdotool xfonts-base
```

#### Direct mode requires --output flag

**Error:** `In direct mode, --output must be specified.`

**Solution:** Always provide `--output` when using `--mode direct`:
```bash
python -m src.main --mode direct --output result.txt --input "Text"
```

#### Permission denied on compiled executable

**Solution:** Make the executable file executable:
```bash
chmod +x dist/type_simulator
```

#### Macro not working as expected

**Solutions:**
1. Use `--dry-run` to validate macro syntax without executing
2. Enable debug logging: `--log-level DEBUG`
3. Check for proper escaping of literal braces with backslash
4. Ensure macro syntax matches documentation (e.g., `{REPEAT_3}` not `{REPEAT 3}`)

```bash
# Validate macro syntax
python -m src.main --mode direct --output test.txt \
  --input "{REPEAT_3}Test{/REPEAT}" --dry-run --log-level DEBUG
```

#### Focus mode not typing in the right window

**Solution:**
1. Ensure the target window is focused before running the command
2. Add a wait at the start: `{WAIT_2}Your text here`
3. Use `--pre-launch-cmd` to focus the window programmatically

#### Typing too fast or slow

**Solution:** Adjust speed and variance:
```bash
# Slower typing
python -m src.main --mode focus --input "Slow" --speed 0.2 --variance 0.08

# Faster typing
python -m src.main --mode focus --input "Fast" --speed 0.03 --variance 0.01

# Or use profiles
python -m src.main --mode focus --input "Text" --profile slow
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
python -m src.main --mode focus --input "Debug test" --log-level DEBUG
```

### Getting Help

```bash
# Show help message
python -m src.main --help

# Show version
python -m src.main --version

# List available profiles
python -m src.main --list-profiles
```

## 🔧 Customization

### Adding Custom Special Keys

Extend `src/type_simulator/text_typer/text_typer.py` to handle additional key sequences or commands.

### Custom Typing Profiles

Edit `src/type_simulator/profiles.py` to add your own typing profiles:

```python
"custom": TypingProfile(
    name="custom",
    speed=0.06,
    variance=0.03,
    pause_probability=0.08,
    pause_duration=0.25,
    description="My custom typing style",
),
```

### Platform-Specific Behavior

The tool uses PyAutoGUI which adapts to different platforms automatically. Key names may vary:
- Windows: `win` key
- Mac: `cmd` key  
- Linux: `super` key (or `win`)

## 📝 Contributing

Contributions are welcome! Please follow these steps:

### Development Setup

```bash
# Clone the repository
git clone https://github.com/djeada/Type-Simulator.git
cd Type-Simulator

# Install development dependencies
pip install -r requirements-dev.txt

# Install project in editable mode
pip install -e .
```

### Running Tests

```bash
# Run unit tests
pytest tests/unit_tests/

# Run end-to-end tests
pytest tests/e2e/

# Run all tests with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit_tests/test_type_simulator/test_text_typer/test_parser.py
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### What to Contribute

- Bug fixes
- New typing profiles
- Additional macro commands
- Platform-specific improvements
- Documentation improvements
- Test coverage improvements
- Performance optimizations

## 📜 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

```
MIT License

Copyright (c) 2024 Type-Simulator Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

- Built with [PyAutoGUI](https://pyautogui.readthedocs.io/) for cross-platform automation
- Compiled with [Nuitka](https://nuitka.net/) for standalone executables
- Inspired by the need for realistic typing demonstrations and automation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/djeada/Type-Simulator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/djeada/Type-Simulator/discussions)
- **Documentation**: This README and inline code documentation

---

**Happy Typing! 🚀**
