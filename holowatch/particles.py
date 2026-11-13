"""NumPy particle systems that drive the hologram (no Panda3D dependency).

Every update() returns (positions (N,3), colours (N,4)) in WORLD space so the
render layer only has to upload two arrays.
"""
from __future__ import annotations
import numpy as np
from . import config as C


def ease(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


class ParticleField:
    """Formation particles (assemble into the watch surface) + ambient floaters."""

    def __init__(self, targets_local, n_ambient=450, seed=11):
        rng = np.random.default_rng(seed)
        self.rng = rng
        self.targets = np.asarray(targets_local, np.float32)
        self.nf = len(self.targets)
        self.na = n_ambient
        # formation start: scattered in a wide cylinder around the platform
        r = rng.uniform(3.0, 11.0, self.nf)
        a = rng.uniform(0, 2 * np.pi, self.nf)
        z = rng.uniform(C.PLATFORM_Z, C.PLATFORM_Z + 9.0, self.nf)
        self.start = np.stack([r * np.cos(a), r * np.sin(a), z], 1).astype(np.float32)
        self.delay = rng.uniform(0.0, 0.55, self.nf).astype(np.float32)
        self.phase = rng.uniform(0, 6.28, self.nf).astype(np.float32)
        self.swirl = rng.uniform(0.6, 2.2, self.nf).astype(np.float32)
        # ambient floaters
        self.a_r = rng.uniform(2.4, 6.5, na := n_ambient).astype(np.float32)
        self.a_ang = rng.uniform(0, 2 * np.pi, na).astype(np.float32)
        self.a_w = rng.uniform(-0.35, 0.35, na).astype(np.float32)
        self.a_z = rng.uniform(C.PLATFORM_Z, C.PLATFORM_Z + 10.0, na).astype(np.float32)
        self.a_vz = rng.uniform(0.25, 0.9, na).astype(np.float32)
        self.a_ph = rng.uniform(0, 6.28, na).astype(np.float32)
        self.total = self.nf + self.na

    def update(self, dt, t, form, mat, settled_alpha=1.0, ambient_alpha=1.0, bright=1.0):
        # ---------------- formation set
        p = np.clip((form - self.delay) / 0.45, 0.0, 1.0)
        e = ease(p)[:, None]
        target = self.targets @ mat[:3, :3] + mat[3, :3]
        pos_f = self.start + (target - self.start) * e
        amp = (1 - p) * p * 4.0 * self.swirl
        ang = self.phase + t * 2.5
        pos_f[:, 0] += amp * np.cos(ang)
        pos_f[:, 1] += amp * np.sin(ang)
        jit = 0.025 * np.sin(t * 4.0 + self.phase * 3.0)
        pos_f[:, 2] += jit * p
        travelling = (p > 0.0) & (p < 1.0)
        settled = p >= 1.0
        tw = 0.5 + 0.5 * np.sin(t * 3.0 + self.phase)
        alpha = np.where(travelling, 0.9, np.where(settled, (0.25 + 0.35 * tw) * settled_alpha, 0.0))
        alpha = np.where(p <= 0.0, 0.25 * (form > 0.01), alpha)
        col_f = np.empty((self.nf, 4), np.float32)
        mix = np.where(travelling, 0.7, 0.2 + 0.3 * tw)
        col_f[:, 0] = (0.15 + 0.7 * mix) * bright
        col_f[:, 1] = (0.85 + 0.15 * mix) * bright
        col_f[:, 2] = 1.0 * bright
        col_f[:, 3] = alpha
        # ---------------- ambient set
        self.a_ang += self.a_w * dt
        self.a_z += self.a_vz * dt
        span = 10.0
        wrap = self.a_z > C.PLATFORM_Z + span
        self.a_z[wrap] -= span
        h = (self.a_z - C.PLATFORM_Z) / span
        pos_a = np.stack([self.a_r * np.cos(self.a_ang), self.a_r * np.sin(self.a_ang), self.a_z], 1)
        fade = np.sin(np.pi * np.clip(h, 0, 1))
        a_alpha = fade * (0.35 + 0.35 * np.sin(t * 2.0 + self.a_ph)) * ambient_alpha * min(1.0, form * 1.5)
        col_a = np.empty((self.na, 4), np.float32)
        col_a[:, 0], col_a[:, 1], col_a[:, 2] = 0.3 * bright, 0.9 * bright, 1.0 * bright
        col_a[:, 3] = np.clip(a_alpha, 0, 1)
        return np.vstack([pos_f, pos_a]).astype(np.float32), np.vstack([col_f, col_a])


class EdgeRunners:
    """Light pulses travelling around watch outlines (with fading trails)."""

    def __init__(self, outlines_local, runners_per_outline=2, trail=18):
        self.outlines = [np.asarray(o, np.float32) for o in outlines_local]
        self.trail = trail
        self.rpo = runners_per_outline
        self.total = len(self.outlines) * runners_per_outline * trail
        self.u = [np.linspace(0, 1, runners_per_outline, endpoint=False) + 0.13 * i
                  for i in range(len(self.outlines))]

    def update(self, dt, mat, level=1.0, speed=0.22):
        pos, col = [], []
        for oi, outline in enumerate(self.outlines):
            n = len(outline)
            self.u[oi] = (self.u[oi] + dt * speed * (1 if oi % 2 == 0 else -1)) % 1.0
            for u in self.u[oi]:
                for k in range(self.trail):
                    idx = (u * n - k * 0.55) % n
                    i0 = int(idx) % n
                    f = idx - int(idx)
                    pt = outline[i0] * (1 - f) + outline[(i0 + 1) % n] * f
                    pos.append(pt)
                    fade = (1 - k / self.trail) ** 1.6
                    col.append((0.6 + 0.4 * fade, 1.0, 1.0, fade * level))
        pos = np.asarray(pos, np.float32) @ mat[:3, :3] + mat[3, :3]
        return pos.astype(np.float32), np.asarray(col, np.float32)


class DataStreams:
    """Vertical columns of upward-flowing dashes (digital data streams)."""

    def __init__(self, columns=12, dashes=6, seed=5):
        rng = np.random.default_rng(seed)
        self.n = columns * dashes
        self.col_ang = np.repeat(np.linspace(0, 2 * np.pi, columns, endpoint=False), dashes).astype(np.float32)
        self.col_r = np.repeat(rng.uniform(4.6, 5.6, columns), dashes).astype(np.float32)
        self.z = rng.uniform(0, 10, self.n).astype(np.float32)
        self.speed = np.repeat(rng.uniform(1.2, 3.2, columns), dashes).astype(np.float32)
        self.len = rng.uniform(0.15, 0.7, self.n).astype(np.float32)
        self.total = self.n * 2

    def update(self, dt, t, level=1.0):
        span = 10.0
        self.z = (self.z + self.speed * dt) % span
        ang = self.col_ang + t * 0.15
        x, y = self.col_r * np.cos(ang), self.col_r * np.sin(ang)
        z0 = C.PLATFORM_Z + self.z
        pos = np.empty((self.n * 2, 3), np.float32)
        pos[0::2] = np.stack([x, y, z0], 1)
        pos[1::2] = np.stack([x, y, z0 + self.len], 1)
        h = self.z / span
        a = np.sin(np.pi * h) * 0.6 * level
        col = np.empty((self.n * 2, 4), np.float32)
        col[:, 0], col[:, 1], col[:, 2] = 0.2, 0.9, 1.0
        col[0::2, 3] = a
        col[1::2, 3] = a * 0.3
        return pos, col


def label_links(anchors_local, label_world, mat, level=1.0, t=0.0):
    """Connection lines watch-anchor -> elbow -> label, plus a travelling dot.
    Returns (line_pos, line_col, dot_pos, dot_col)."""
    anchors = np.asarray(anchors_local, np.float32) @ mat[:3, :3] + mat[3, :3]
    labels = np.asarray(label_world, np.float32)
    k = len(labels)
    lp = np.empty((k * 4, 3), np.float32)
    lc = np.empty((k * 4, 4), np.float32)
    dots = np.empty((k * 2, 3), np.float32)
    for i in range(k):
        a, l = anchors[i], labels[i]
        elbow = np.array([l[0] * 0.55 + a[0] * 0.45, a[1], l[2]], np.float32)
        lp[4 * i:4 * i + 4] = [a, elbow, elbow, l + np.array([-np.sign(l[0]) * 1.5, 0, 0], np.float32)]
        s = (t * 0.5 + i * 0.17) % 1.0
        dots[2 * i] = a + (elbow - a) * s
        dots[2 * i + 1] = a
    lc[:] = (0.3, 0.95, 1.0, 0.55 * level)
    dcol = np.empty((k * 2, 4), np.float32)
    dcol[:] = (0.8, 1.0, 1.0, 0.9 * level)
    return lp, lc, dots, dcol
