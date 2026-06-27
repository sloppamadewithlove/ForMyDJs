import array
import math

from app.server import estimate_bpm

RATE = 8000


def _groove(bpm, seconds=40, sub=0.0):
    """Synthesise a kick on every beat (plus optional weaker eighth-note hats)
    so we can assert the estimator locks onto the beat, not a subdivision."""
    period = RATE * 60.0 / bpm
    samples = array.array("f", [0.0] * int(RATE * seconds))
    kick_len = int(RATE * 0.05)

    def place(center, amp, freq):
        start = int(round(center))
        for j in range(kick_len):
            if start + j >= len(samples):
                break
            t = j / RATE
            samples[start + j] += math.sin(2 * math.pi * freq * t) * math.exp(-t * 40.0) * amp

    i = 0
    while i * period < len(samples):
        place(i * period, 1.0, 60.0)              # strong low kick on the beat
        if sub > 0:
            place((i + 0.5) * period, sub, 200.0)  # weaker off-beat hat
        i += 1
    return samples


def test_estimate_bpm_returns_the_beat():
    assert abs(estimate_bpm(_groove(123), RATE) - 123) <= 2


def test_estimate_bpm_does_not_double_into_a_subdivision():
    # Strong off-beat hats used to push detection up an octave (e.g. 123 -> 162).
    bpm = estimate_bpm(_groove(124, sub=0.7), RATE)
    assert abs(bpm - 124) <= 2


def test_estimate_bpm_handles_house_and_techno_tempos():
    for tempo in (120, 126, 128, 130):
        assert abs(estimate_bpm(_groove(tempo), RATE) - tempo) <= 2


def test_estimate_bpm_none_on_silence():
    assert estimate_bpm(array.array("f", [0.0] * (RATE * 5)), RATE) is None


def test_estimate_bpm_none_when_too_short():
    assert estimate_bpm(array.array("f", [0.1] * 100), RATE) is None
