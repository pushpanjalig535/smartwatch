"""Simulated (demo) health/fitness data.  Everything here is fake and labelled
as DEMO DATA wherever it is shown."""
from __future__ import annotations
import time
import numpy as np

ECG_LEN = 240


def ecg_shape(phase):
    """One synthetic PQRST cycle, phase in [0,1)."""
    g = lambda c, w, a: a * np.exp(-((phase - c) / w) ** 2)
    return g(0.16, 0.035, 0.12) + g(0.285, 0.012, -0.15) + g(0.31, 0.012, 1.0) \
        + g(0.335, 0.014, -0.28) + g(0.55, 0.05, 0.25)


class Telemetry:
    def __init__(self, seed=3):
        self.rng = np.random.default_rng(seed)
        self.hr, self.hr_target = 76.0, 76.0
        self.spo2, self.temp = 98.0, 36.6
        self.steps, self.calories, self.distance = 6245.0, 312.0, 4.8
        self.workout = 42 * 60 + 15.0
        self.sleep_min = 7 * 60 + 24
        self.battery = 87.0
        self.activity = 0.72
        self.phase = 0.0
        self.beat = 0.0
        self.ecg = np.zeros(ECG_LEN)
        self._carry = 0.0
        self._t = 0.0
        self._next_target = 2.0

    def update(self, dt):
        self._t += dt
        if self._t > self._next_target:
            self.hr_target = float(np.clip(self.hr_target + self.rng.normal(0, 3), 70, 84))
            self._next_target = self._t + self.rng.uniform(1.5, 3.5)
        self.hr += (self.hr_target - self.hr) * min(1.0, dt * 0.8)
        self.spo2 = 97.5 + 0.8 * np.sin(self._t * 0.21) + 0.3 * np.sin(self._t * 0.77)
        self.temp = 36.6 + 0.12 * np.sin(self._t * 0.13)
        self.steps += dt * 0.85
        self.calories += dt * 0.031
        self.distance += dt * 0.00064
        self.workout += dt
        self.battery = max(1.0, 87.0 - self._t / 240.0)  # drains 1% / 4 min
        self.activity = 0.72 + 0.02 * np.sin(self._t * 0.05)
        # ECG samples at 60 Hz
        self._carry += dt * 60
        n = int(self._carry)
        self._carry -= n
        if n:
            n = min(n, ECG_LEN)
            ph = (self.phase + (np.arange(1, n + 1)) * self.hr / 3600.0) % 1.0
            self.phase = float(ph[-1])
            vals = ecg_shape(ph) + self.rng.normal(0, 0.015, n)
            self.ecg = np.concatenate([self.ecg[n:], vals])
        d = ((self.phase - 0.31 + 0.5) % 1.0) - 0.5
        self.beat = float(np.exp(-(d / 0.07) ** 2))

    # --- formatted helpers ---------------------------------------------
    @property
    def bpm(self): return int(round(self.hr))
    @property
    def spo2_i(self): return int(round(self.spo2))
    @property
    def steps_i(self): return int(self.steps)
    @property
    def battery_i(self): return int(round(self.battery))

    def workout_str(self):
        s = int(self.workout)
        return f"{s // 3600:02d}:{(s // 60) % 60:02d}:{s % 60:02d}"

    @staticmethod
    def clock():
        lt = time.localtime()
        return (time.strftime("%H:%M", lt), time.strftime("%S", lt),
                time.strftime("%a %d %b", lt).upper())
