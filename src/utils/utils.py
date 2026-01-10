import platform
import shutil
import subprocess


def is_program_installed(program):
    """Check if a program is installed and available in the system's PATH."""
    result = subprocess.run(["which", program], capture_output=True, text=True)
    return result.returncode == 0


# Terminal emulators with their metadata
# Format: (executable, command_template, description, install_hint)
LINUX_TERMINALS = [
    ("gnome-terminal", "gnome-terminal -- bash", "GNOME Terminal (default for GNOME/Linux Mint)", 
     "sudo apt install gnome-terminal"),
    ("konsole", "konsole -e bash", "Konsole (default for KDE)", 
     "sudo apt install konsole"),
    ("xfce4-terminal", "xfce4-terminal -e bash", "XFCE Terminal (default for XFCE)", 
     "sudo apt install xfce4-terminal"),
    ("mate-terminal", "mate-terminal -e bash", "MATE Terminal (default for MATE)", 
     "sudo apt install mate-terminal"),
    ("tilix", "tilix -e bash", "Tilix (tiling terminal)", 
     "sudo apt install tilix"),
    ("kitty", "kitty bash", "Kitty (GPU-accelerated terminal)", 
     "sudo apt install kitty"),
    ("alacritty", "alacritty -e bash", "Alacritty (GPU-accelerated terminal)", 
     "sudo apt install alacritty"),
    ("xterm", "xterm -e bash", "XTerm (classic X11 terminal)", 
     "sudo apt install xterm"),
]


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
        for executable, cmd_template, _, _ in LINUX_TERMINALS:
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


def check_terminal_availability():
    """
    Check and display terminal emulator availability on the system.
    
    Iterates through all supported terminals and displays:
    - Which terminals are available
    - Which are not installed and how to install them
    - Platform-specific information
    
    Returns a tuple of (available_terminals, unavailable_terminals)
    where each is a list of tuples (name, details).
    """
    system = platform.system()
    available = []
    unavailable = []
    
    print("\n🖥️  Terminal Emulator Availability Check")
    print("=" * 60)
    print(f"  Platform: {system}")
    print("=" * 60)
    
    if system == "Darwin":
        # macOS always has Terminal.app
        print("\n✅ macOS detected - Terminal.app is built-in")
        print("   Command: open -a Terminal")
        print("\n   Other options:")
        # Check for iTerm2
        if shutil.which("iTerm"):
            print("   ✅ iTerm2 is installed")
            available.append(("iTerm2", "Available"))
        else:
            print("   ℹ️  iTerm2 not installed (optional)")
            print("      Install: brew install --cask iterm2")
            unavailable.append(("iTerm2", "Not installed (optional)"))
        available.append(("Terminal.app", "Built-in"))
        
    elif system == "Linux":
        print("\n📋 Checking Linux terminal emulators:\n")
        
        for executable, cmd_template, description, install_hint in LINUX_TERMINALS:
            path = shutil.which(executable)
            if path:
                print(f"   ✅ {executable}")
                print(f"      Path: {path}")
                print(f"      Description: {description}")
                print(f"      Command: {cmd_template}")
                available.append((executable, path))
            else:
                print(f"   ❌ {executable}")
                print(f"      Description: {description}")
                print(f"      Not installed - Install with: {install_hint}")
                unavailable.append((executable, install_hint))
            print()
        
    elif system == "Windows":
        print("\n✅ Windows detected - cmd.exe is built-in")
        print("   Command: cmd.exe /k")
        available.append(("cmd.exe", "Built-in"))
        
        # Check for Windows Terminal
        wt_path = shutil.which("wt")
        if wt_path:
            print("\n   ✅ Windows Terminal is installed")
            print(f"      Path: {wt_path}")
            available.append(("Windows Terminal", wt_path))
        else:
            print("\n   ℹ️  Windows Terminal not installed (optional)")
            print("      Install from Microsoft Store or: winget install Microsoft.WindowsTerminal")
            unavailable.append(("Windows Terminal", "Not installed (optional)"))
            
        # Check for PowerShell
        ps_path = shutil.which("pwsh")
        if ps_path:
            print("\n   ✅ PowerShell Core is installed")
            print(f"      Path: {ps_path}")
            available.append(("PowerShell Core", ps_path))
        else:
            print("\n   ℹ️  PowerShell Core not installed (optional)")
            print("      Install: winget install Microsoft.PowerShell")
            unavailable.append(("PowerShell Core", "Not installed (optional)"))
    else:
        print(f"\n⚠️  Unsupported platform: {system}")
        print("   Terminal mode may not work on this platform.")
        print("   You can specify a custom terminal with --editor-script.")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    if available:
        print(f"   ✅ Available terminals: {len(available)}")
        default_cmd, _ = get_default_terminal_command()
        if default_cmd:
            print(f"   🎯 Default command: {default_cmd}")
    else:
        print("   ❌ No terminal emulators found!")
        print("   Please install one of the supported terminals.")
    
    if unavailable and system == "Linux":
        print(f"\n   ℹ️  {len(unavailable)} terminals not installed")
        print("   Run with --log-level DEBUG for installation commands")
    
    print()
    
    return available, unavailable


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
