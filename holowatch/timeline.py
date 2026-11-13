"""Cinematic startup timeline + steady-state level computation (pure Python).

levels(t) maps elapsed time to a dict of 0..1 "levels" that drive every visual
(platform, pulse, rings, beams, particle formation, wire/face reveal, screen
power-on, message, dashboard).  After the intro, steady_levels(proj) is used so
the projection toggle can dissolve / reform the hologram.
"""
from __future__ import annotations

INTRO_DURATION = 16.5
SCREEN_ON_TIME = 10.6
HEALTH_PAGE_TIME = 11.8
MESSAGE = "SMARTWATCH HOLOGRAPHIC PROJECTION INITIALIZED"

CAPTIONS = [
    (0.0, 1.0, ""),
    (1.0, 2.8, "PROJECTION PLATFORM POWERING UP"),
    (2.8, 4.4, "ENERGY PULSE DETECTED"),
    (4.4, 6.0, "SCANNING RINGS ENGAGED // BEAMS ASCENDING"),
    (6.0, 9.6, "GATHERING PARTICLES // RECONSTRUCTING SMARTWATCH"),
    (9.6, 10.6, "STABILISING HOLOGRAPHIC MATRIX"),
    (10.6, 11.8, "DISPLAY ONLINE"),
    (11.8, 12.0, "ACTIVATING HEALTH-MONITORING INTERFACE"),
]


def smooth(x, a=0.0, b=1.0):
    """Smoothstep of x between a and b."""
    if b == a:
        return 1.0 if x >= b else 0.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def caption(t):
    for a, b, s in CAPTIONS:
        if a <= t < b:
            return s
    return "ACTIVATING HEALTH-MONITORING INTERFACE" if 11.8 <= t < 13.2 else ""


def levels(t):
    pulse_p = smooth(t, 2.8, 4.4)
    flash = max(0.0, 1.0 - abs(t - 3.0) / 0.45)  # bright energy burst at t=3
    return {
        "platform": smooth(t, 0.8, 2.2),
        "platform_scale": 0.30 + 0.70 * smooth(t, 3.0, 6.5),
        "pulse": pulse_p if 2.8 <= t < 4.4 else 0.0,
        "flash": flash,
        "rings": smooth(t, 3.2, 5.0),
        "beams": smooth(t, 4.0, 5.6),
        "form": smooth(t, 4.6, 9.6),
        "wire": smooth(t, 8.6, 10.2),
        "face": smooth(t, 9.4, 10.8),
        "screen": smooth(t, SCREEN_ON_TIME, 11.7),
        "message": smooth(t, 11.9, 12.4) * (1 - smooth(t, 15.4, 16.2)),
        "typed": smooth(t, 12.0, 14.0),
        "ui": smooth(t, 11.0, 12.4),
        "done": t >= INTRO_DURATION,
    }


def steady_levels(proj):
    """Levels after the intro; proj in [0,1] is the (eased) projection state."""
    return {
        "platform": 1.0, "platform_scale": 1.0, "pulse": 0.0, "flash": 0.0,
        "rings": 0.30 + 0.70 * proj,
        "beams": proj,
        "form": proj,
        "wire": smooth(proj, 0.55, 0.85),
        "face": smooth(proj, 0.70, 1.0),
        "screen": smooth(proj, 0.80, 1.0),
        "message": 0.0, "typed": 1.0, "ui": 1.0, "done": True,
    }
