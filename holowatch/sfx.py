"""Procedurally generated sound effects (NumPy -> temporary WAV files).
No audio assets are shipped; if audio is unavailable everything silently no-ops."""
from __future__ import annotations
import os
import tempfile
import wave
import numpy as np

SR = 22050


def _write(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32000).astype(np.int16).tobytes())


def _env(n, a=0.01, r=0.3):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def make_sounds(folder):
    t = lambda d: np.arange(int(SR * d)) / SR
    sounds = {}
    tt = t(1.6)
    sweep = np.sin(2 * np.pi * (80 * tt + 420 * tt ** 2)) * _env(len(tt), 0.05, 0.6) * 0.5
    sounds["pulse"] = sweep
    tt = t(0.12)
    sounds["click"] = np.sin(2 * np.pi * 1400 * tt) * _env(len(tt), 0.002, 0.03) * 0.4
    tt = t(0.2)
    sounds["beep"] = (np.sin(2 * np.pi * 880 * tt) + 0.5 * np.sin(2 * np.pi * 1320 * tt)) * _env(len(tt), 0.004, 0.08) * 0.3
    tt = t(0.5)
    sounds["sos"] = np.sign(np.sin(2 * np.pi * 620 * tt)) * (np.sin(2 * np.pi * 6 * tt) > 0) * 0.15
    tt = t(1.2)
    sounds["whoosh"] = np.random.default_rng(1).normal(0, 1, len(tt)) * np.sin(np.pi * tt / 1.2) ** 2 * 0.12
    tt = t(2.0)  # seamless hum loop
    hum = 0.25 * np.sin(2 * np.pi * 55 * tt) + 0.12 * np.sin(2 * np.pi * 110 * tt) + 0.05 * np.sin(2 * np.pi * 165 * tt)
    sounds["hum"] = hum
    paths = {}
    for k, v in sounds.items():
        p = os.path.join(folder, k + ".wav")
        _write(p, v)
        paths[k] = p
    return paths


class Sfx:
    def __init__(self, loader):
        self.s = {}
        try:
            folder = tempfile.mkdtemp(prefix="holowatch_sfx_")
            for k, p in make_sounds(folder).items():
                from panda3d.core import Filename
                self.s[k] = loader.loadSfx(Filename.fromOsSpecific(p))
            if "hum" in self.s:
                self.s["hum"].setLoop(True)
                self.s["hum"].setVolume(0.25)
        except Exception as e:  # audio is optional
            print("[sfx] audio disabled:", e)
            self.s = {}

    def play(self, name, vol=1.0):
        snd = self.s.get(name)
        if snd:
            snd.setVolume(vol)
            snd.play()

    def start_hum(self):
        if "hum" in self.s:
            self.s["hum"].play()
