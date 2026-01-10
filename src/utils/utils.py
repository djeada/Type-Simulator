import platform
import shutil
import subprocess


def is_program_installed(program):
    """Check if a program is installed and available in the system's PATH."""
    result = subprocess.run(["which", program], capture_output=True, text=True)
    return result.returncode == 0


def get_default_terminal_command():
    """
    Detect and return a command to open a terminal emulator.
    
    Returns a tuple of (command_string, None) on success,
    or (None, error_message) if no terminal is found.
    
    Supports:
    - Linux: gnome-terminal, konsole, xfce4-terminal, mate-terminal, 
             tilix, kitty, alacritty, xterm
    - macOS: Terminal.app (via 'open -a Terminal')
    - Windows: cmd.exe
    """
    system = platform.system()
    
    if system == "Darwin":
        # macOS: Use 'open -a Terminal' to open Terminal.app
        # This creates a new terminal window and returns immediately
        return ("open -a Terminal", None)
    
    elif system == "Linux":
        # Linux: Try common terminal emulators in order of preference
        # Format: (executable, command_template)
        # command_template uses {cmd} as placeholder for the shell command
        terminals = [
            # GNOME/Linux Mint default
            ("gnome-terminal", "gnome-terminal -- bash"),
            # KDE
            ("konsole", "konsole -e bash"),
            # XFCE
            ("xfce4-terminal", "xfce4-terminal -e bash"),
            # MATE
            ("mate-terminal", "mate-terminal -e bash"),
            # Tilix
            ("tilix", "tilix -e bash"),
            # Modern terminals
            ("kitty", "kitty bash"),
            ("alacritty", "alacritty -e bash"),
            # Classic fallback
            ("xterm", "xterm -e bash"),
        ]
        
        for executable, cmd_template in terminals:
            if shutil.which(executable):
                return (cmd_template, None)
        
        # No terminal found
        return (
            None,
            "No terminal emulator found. Please install one of: "
            "gnome-terminal, konsole, xfce4-terminal, mate-terminal, "
            "tilix, kitty, alacritty, or xterm. "
            "Alternatively, specify a terminal with --editor-script."
        )
    
    elif system == "Windows":
        # Windows: Use cmd.exe
        return ("cmd.exe /k", None)
    
    else:
        return (
            None,
            f"Unsupported platform: {system}. "
            "Please specify a terminal command with --editor-script."
        )


def get_focus_mode_dependency(platform_name):
    """Get the required dependency for focus mode based on platform."""
    dependencies = {
        "Linux": "xdotool",
        "Darwin": "osascript",  # Part of macOS
        "Windows": None,  # Uses pyautogui directly
    }
    return dependencies.get(platform_name)


def install_instructions(program):
    """Provide installation instructions for missing programs."""
    instructions = {
        "xclip": "Install xclip using your package manager, e.g., 'sudo apt-get install xclip' for Debian/Ubuntu.",
        "pyautogui": "Install pyautogui using pip, e.g., 'pip install pyautogui'.",
        "xdotool": "Install xdotool using your package manager, e.g., 'sudo apt-get install xdotool' for Debian/Ubuntu.",
    }
    return instructions.get(
        program, f"No installation instructions available for {program}."
    )
