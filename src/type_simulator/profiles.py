# src/type_simulator/profiles.py
"""
Typing profiles for Type-Simulator.

Provides preset typing patterns that simulate different typing styles:
- human: Natural typing with realistic variations
- fast: Quick professional typing
- slow: Careful, deliberate typing
- robotic: Mechanical, consistent typing
- hunt_and_peck: Slow, searching for keys
- programmer: Fast with occasional pauses for thinking
- storyteller: Dramatic pauses between sentences
- casual: Relaxed typing with irregular rhythm
- expert: Ultra-fast professional typing
- nervous: Quick bursts with hesitations
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TypingProfile:
    """
    Configuration for a typing style.

    Attributes:
        name: Profile identifier
        speed: Base seconds per character
        variance: Random variance in timing (±variance seconds)
        pause_probability: Chance of micro-pause between words (0.0-1.0)
        pause_duration: Base duration of micro-pauses in seconds
        description: Human-readable description of the profile
    """

    name: str
    speed: float
    variance: float
    pause_probability: float
    pause_duration: float
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
    "programmer": TypingProfile(
        name="programmer",
        speed=0.05,
        variance=0.03,
        pause_probability=0.2,
        pause_duration=0.4,
        description="Fast typing with thinking pauses for coding",
    ),
    "storyteller": TypingProfile(
        name="storyteller",
        speed=0.1,
        variance=0.05,
        pause_probability=0.25,
        pause_duration=0.6,
        description="Dramatic typing with pauses for effect",
    ),
    "casual": TypingProfile(
        name="casual",
        speed=0.12,
        variance=0.08,
        pause_probability=0.15,
        pause_duration=0.35,
        description="Relaxed, informal typing rhythm",
    ),
    "expert": TypingProfile(
        name="expert",
        speed=0.02,
        variance=0.005,
        pause_probability=0.03,
        pause_duration=0.05,
        description="Ultra-fast professional touch typist",
    ),
    "nervous": TypingProfile(
        name="nervous",
        speed=0.06,
        variance=0.04,
        pause_probability=0.3,
        pause_duration=0.25,
        description="Quick bursts with frequent hesitations",
    ),
}


def get_profile(name: str) -> Optional[TypingProfile]:
    """
    Get a typing profile by name.

    Args:
        name: Profile name (case-insensitive)

    Returns:
        TypingProfile if found, None otherwise
    """
    return PROFILES.get(name.lower())


def list_profiles() -> Dict[str, TypingProfile]:
    """
    List all available typing profiles.

    Returns:
        Dictionary of profile name to TypingProfile
    """
    return PROFILES.copy()
