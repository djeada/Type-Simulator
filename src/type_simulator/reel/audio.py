"""
Procedural audio for reels, using only the standard library:

- keyboard click sounds placed at each key press
- a royalty-free synthwave loop (pads, bass, arpeggio, drums) so reels have
  music without licensing worries; users can pass their own track instead
"""

import math
import random
import wave
from array import array
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

SAMPLE_RATE = 44100
_TABLE_SIZE = 2048


# ─────────────────────────── helpers ───────────────────────────
def _wavetable(harmonics: Sequence[float]) -> List[float]:
    table = [0.0] * _TABLE_SIZE
    for h, amp in enumerate(harmonics, 1):
        if amp:
            for i in range(_TABLE_SIZE):
                table[i] += amp * math.sin(2 * math.pi * h * i / _TABLE_SIZE)
    peak = max(abs(v) for v in table) or 1.0
    return [v / peak for v in table]


_SOFT_SAW = _wavetable([1, 0.45, 0.25, 0.12, 0.06])
_WARM = _wavetable([1, 0.5, 0.15])
_SQUAREISH = _wavetable([1, 0, 0.3, 0, 0.12, 0, 0.05])


def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _osc(buf, start, length, freq, table, amp, attack, decay=None, release=0.0):
    """Add an enveloped wavetable oscillator to `buf` (in place)."""
    sr = SAMPLE_RATE
    inc = freq * _TABLE_SIZE / sr
    phase = random.random() * _TABLE_SIZE
    end = min(len(buf), start + length)
    att = max(1, int(attack * sr))
    rel = int(release * sr)
    k = math.exp(-1.0 / (decay * sr)) if decay else 1.0
    env_decay = 1.0
    for n in range(start, end):
        i = n - start
        env = amp * (i / att if i < att else 1.0) * env_decay
        if rel and end - n < rel:
            env *= (end - n) / rel
        buf[n] += env * table[int(phase) % _TABLE_SIZE]
        phase += inc
        env_decay *= k


def _noise(buf, start, length, amp, decay, highpass=0.0, rng=random):
    end = min(len(buf), start + length)
    k = math.exp(-1.0 / (decay * SAMPLE_RATE))
    env, low = amp, 0.0
    for n in range(start, end):
        x = rng.random() * 2 - 1
        low += (x - low) * (1 - highpass)  # one-pole low-pass
        buf[n] += env * (x - low if highpass else x)
        env *= k


def write_wav(path: Path, samples: Sequence[float]) -> None:
    peak = max((abs(s) for s in samples), default=0.0)
    gain = 0.95 / peak if peak > 0.95 else 1.0
    data = array("h", (int(max(-1.0, min(1.0, s * gain)) * 32767) for s in samples))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(data.tobytes())


# ─────────────────────────── key clicks ───────────────────────────
def _click(rng: random.Random, body_hz: float, loud: float) -> List[float]:
    length = int(0.07 * SAMPLE_RATE)
    buf = [0.0] * length
    _noise(buf, 0, int(0.01 * SAMPLE_RATE), 0.4 * loud, 0.0015, highpass=0.6, rng=rng)
    _osc(
        buf,
        0,
        length,
        body_hz * rng.uniform(0.92, 1.08),
        _WARM,
        0.35 * loud,
        0.0005,
        decay=0.012,
    )
    # Second, softer "bottom-out" tick
    tick = int(rng.uniform(0.016, 0.024) * SAMPLE_RATE)
    _noise(
        buf, tick, int(0.006 * SAMPLE_RATE), 0.18 * loud, 0.001, highpass=0.7, rng=rng
    )
    return buf


def render_clicks(
    sounds: Sequence[Tuple[float, str]], duration: float, seed: int = 0
) -> List[float]:
    rng = random.Random(seed)
    variants: Dict[str, List[List[float]]] = {
        "key": [_click(rng, rng.uniform(340, 460), 1.0) for _ in range(6)],
        "space": [_click(rng, rng.uniform(190, 230), 1.15) for _ in range(3)],
        "enter": [_click(rng, rng.uniform(150, 180), 1.35) for _ in range(2)],
    }
    out = [0.0] * (int(duration * SAMPLE_RATE) + SAMPLE_RATE)
    for t, kind in sounds:
        sample = rng.choice(variants.get(kind, variants["key"]))
        gain = rng.uniform(0.75, 1.0)
        start = int(t * SAMPLE_RATE)
        for i, v in enumerate(sample):
            if start + i < len(out):
                out[start + i] += v * gain
    return out


# ─────────────────────────── music ───────────────────────────
# A minor: Am - F - C - G
_CHORDS = [(57, 60, 64), (53, 57, 60), (55, 60, 64), (55, 59, 62)]
_BASS = [45, 41, 48, 43]
BPM = 92


def _render_loop(with_drums: bool, rng: random.Random) -> List[float]:
    beat = 60.0 / BPM
    bar = 4 * beat
    sr = SAMPLE_RATE
    n_bar = int(bar * sr)
    buf = [0.0] * (n_bar * len(_CHORDS))
    duck = [1.0] * len(buf)

    for b, (chord, root) in enumerate(zip(_CHORDS, _BASS)):
        start = b * n_bar
        # Pad: two slightly detuned voices per chord note
        for note in chord:
            for cents in (-6, 6):
                _osc(
                    buf,
                    start,
                    n_bar,
                    _freq(note + cents / 100),
                    _SOFT_SAW,
                    0.045,
                    0.35,
                    release=0.25,
                )
        # Arpeggio in 16ths, one octave up
        pattern = [0, 1, 2, 1, 0, 2, 1, 2]
        step = beat / 4
        for s in range(16):
            note = chord[pattern[s % len(pattern)]] + 12
            _osc(
                buf,
                start + int(s * step * sr),
                int(step * sr * 1.6),
                _freq(note),
                _SQUAREISH,
                0.05,
                0.004,
                decay=0.09,
            )
        if with_drums:
            # Bass in 8ths
            for e in range(8):
                _osc(
                    buf,
                    start + int(e * beat / 2 * sr),
                    int(beat / 2 * sr),
                    _freq(root),
                    _WARM,
                    0.22,
                    0.005,
                    decay=0.16,
                    release=0.02,
                )
            for q in range(4):
                at = start + int(q * beat * sr)
                _kick(buf, at)
                for i in range(int(0.25 * sr)):
                    if at + i < len(duck):
                        duck[at + i] = min(
                            duck[at + i], 1 - 0.55 * math.exp(-i / (0.09 * sr))
                        )
                if q in (1, 3):
                    _noise(buf, at, int(0.25 * sr), 0.22, 0.06, highpass=0.35, rng=rng)
                _noise(
                    buf,
                    at + int(beat / 2 * sr),
                    int(0.05 * sr),
                    0.07,
                    0.012,
                    highpass=0.85,
                    rng=rng,
                )

    # Feedback echo for space
    delay = int(beat * 0.75 * sr)
    for n in range(delay, len(buf)):
        buf[n] += 0.28 * buf[n - delay]
    return [s * d for s, d in zip(buf, duck)]


def _kick(buf, start) -> None:
    sr = SAMPLE_RATE
    phase = 0.0
    for i in range(int(0.3 * sr)):
        n = start + i
        if n >= len(buf):
            break
        t = i / sr
        freq = 45 + 85 * math.exp(-t / 0.03)
        phase += 2 * math.pi * freq / sr
        buf[n] += 0.55 * math.exp(-t / 0.16) * math.sin(phase)


def render_music(duration: float, seed: int = 0) -> List[float]:
    """Synthwave track at least `duration` seconds long: intro, then full loop."""
    rng = random.Random(seed)
    random.seed(seed)
    intro = _render_loop(False, rng)
    main = _render_loop(True, rng)
    out = list(intro)
    while len(out) < duration * SAMPLE_RATE:
        out.extend(main)
    # Gentle saturation keeps peaks musical
    return [math.tanh(1.4 * s) * 0.8 for s in out]
