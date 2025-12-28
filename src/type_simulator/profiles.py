# src/type_simulator/profiles.py
"""
Typing profiles for Type-Simulator.

Provides preset typing patterns that simulate different typing styles:
- human: Natural typing with realistic variations
- fast: Quick professional typing
- slow: Careful, deliberate typing
- robotic: Mechanical, consistent typing
- hunt_and_peck: Slow, searching for keys
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TypingProfile:
    """Configuration for a typing style."""

    name: str
    speed: float  # Base seconds per character
    variance: float  # Random variance in timing
    pause_probability: float  # Chance of micro-pause between words
    pause_duration: float  # Duration of micro-pauses
    description: str


# Pre-defined typing profiles
PROFILES: Dict[str, TypingProfile] = {
    "human": TypingProfile(
        name="human",
        speed=0.08,
        variance=0.04,
        pause_probability=0.1,
        pause_duration=0.3,
        description="Natural human typing with realistic variations",
    ),
    "fast": TypingProfile(
        name="fast",
        speed=0.03,
        variance=0.01,
        pause_probability=0.05,
        pause_duration=0.1,
        description="Quick professional typing",
    ),
    "slow": TypingProfile(
        name="slow",
        speed=0.2,
        variance=0.08,
        pause_probability=0.15,
        pause_duration=0.5,
        description="Careful, deliberate typing",
    ),
    "robotic": TypingProfile(
        name="robotic",
        speed=0.05,
        variance=0.0,
        pause_probability=0.0,
        pause_duration=0.0,
        description="Mechanical, consistent typing with no variance",
    ),
    "hunt_and_peck": TypingProfile(
        name="hunt_and_peck",
        speed=0.4,
        variance=0.2,
        pause_probability=0.3,
        pause_duration=0.8,
        description="Slow, searching for keys typing style",
    ),
}


def get_profile(name: str) -> Optional[TypingProfile]:
    """Get a typing profile by name."""
    return PROFILES.get(name.lower())


def list_profiles() -> Dict[str, TypingProfile]:
    """List all available typing profiles."""
    return PROFILES.copy()
