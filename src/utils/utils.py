import subprocess


def is_program_installed(program):
    """Check if a program is installed and available in the system's PATH."""
    result = subprocess.run(["which", program], capture_output=True, text=True)
    return result.returncode == 0


def install_instructions(program):
    """Provide installation instructions for missing programs."""
    instructions = {
        "xclip": "Install xclip using your package manager, e.g., 'sudo apt-get install xclip' for Debian/Ubuntu.",
        "pyautogui": "Install pyautogui using pip, e.g., 'pip install pyautogui'.",
    }
    return instructions.get(
        program, f"No installation instructions available for {program}."
    )
