import pytest

from type_simulator.profiles import get_profile, list_profiles, TypingProfile


def test_get_profile_human():
    """Test getting the human profile."""
    profile = get_profile("human")
    assert profile is not None
    assert profile.name == "human"
    assert profile.speed == 0.08
    assert profile.variance == 0.04


def test_get_profile_fast():
    """Test getting the fast profile."""
    profile = get_profile("fast")
    assert profile is not None
    assert profile.speed == 0.03
    assert profile.variance == 0.01


def test_get_profile_slow():
    """Test getting the slow profile."""
    profile = get_profile("slow")
    assert profile is not None
    assert profile.speed == 0.2


def test_get_profile_robotic():
    """Test getting the robotic profile."""
    profile = get_profile("robotic")
    assert profile is not None
    assert profile.variance == 0.0


def test_get_profile_hunt_and_peck():
    """Test getting the hunt_and_peck profile."""
    profile = get_profile("hunt_and_peck")
    assert profile is not None
    assert profile.speed == 0.4


def test_get_profile_case_insensitive():
    """Test that profile lookup is case-insensitive."""
    profile = get_profile("HUMAN")
    assert profile is not None
    assert profile.name == "human"


def test_get_profile_nonexistent():
    """Test getting a non-existent profile returns None."""
    profile = get_profile("nonexistent")
    assert profile is None


def test_list_profiles():
    """Test listing all profiles."""
    profiles = list_profiles()
    assert len(profiles) >= 5
    assert "human" in profiles
    assert "fast" in profiles
    assert "slow" in profiles
    assert "robotic" in profiles
    assert "hunt_and_peck" in profiles


# Tests for new profiles


def test_get_profile_programmer():
    """Test getting the programmer profile."""
    profile = get_profile("programmer")
    assert profile is not None
    assert profile.name == "programmer"
    assert profile.speed == 0.05
    assert profile.variance == 0.03


def test_get_profile_storyteller():
    """Test getting the storyteller profile."""
    profile = get_profile("storyteller")
    assert profile is not None
    assert profile.name == "storyteller"
    assert profile.speed == 0.1
    assert profile.pause_probability == 0.25


def test_get_profile_casual():
    """Test getting the casual profile."""
    profile = get_profile("casual")
    assert profile is not None
    assert profile.name == "casual"
    assert profile.speed == 0.12


def test_get_profile_expert():
    """Test getting the expert profile."""
    profile = get_profile("expert")
    assert profile is not None
    assert profile.name == "expert"
    assert profile.speed == 0.02
    assert profile.variance == 0.005


def test_get_profile_nervous():
    """Test getting the nervous profile."""
    profile = get_profile("nervous")
    assert profile is not None
    assert profile.name == "nervous"
    assert profile.speed == 0.06
    assert profile.pause_probability == 0.3


def test_list_profiles_includes_new():
    """Test that list_profiles includes all new profiles."""
    profiles = list_profiles()
    assert len(profiles) >= 10  # 5 original + 5 new
    new_profiles = ["programmer", "storyteller", "casual", "expert", "nervous"]
    for name in new_profiles:
        assert name in profiles, f"Profile '{name}' not found in profiles"
