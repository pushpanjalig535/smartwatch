"""Procedural 3D smartwatch geometry (pure NumPy).

build_watch() returns a list of Part objects.  Each Part carries its mesh, a
colour, a "kind" (controls how it behaves in X-ray mode) and an explode vector
used by the disassembly animation.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from . import config as C
from .mesh import Mesh, rrect, ring3, loft, box, cylinder


@dataclass
class Part:
    name: str
    mesh: Mesh
    color: tuple
    kind: str            # 'shell' | 'internal'
    explode: tuple       # offset applied at full disassembly
    face_alpha: float = 0.16
    edge_alpha: float = 0.9


A, B, R = C.CASE_HALF_W, C.CASE_HALF_H, C.CASE_RADIUS
T = C.CASE_HALF_T
ARC, SUB = 12, 3


def _ring(inset, y):
    return ring3(rrect(A - inset, B - inset, R - inset, ARC, SUB), y)


def screen_half_size():
    return A - C.SCREEN_INSET, B - C.SCREEN_INSET


SCREEN_Y = -T - 0.01


def _case():
    spec = [(0.34, -0.43), (0.34, -0.47), (0.16, -0.47), (0.06, -0.43), (0.0, -0.33),
            (0.0, 0.25), (0.06, 0.38), (0.22, 0.45), (0.48, 0.45)]
    return loft([_ring(i, y) for i, y in spec], lstride=3)


def _glass():
    spec = [(0.34, -0.47), (0.55, -0.505), (1.0, -0.52)]
    return loft([_ring(i, y) for i, y in spec], cap_end=(0, -0.527, 0), lstride=3)


def _back():
    spec = [(0.48, 0.45), (0.70, 0.53), (1.0, 0.55)]
    return loft([_ring(i, y) for i, y in spec], cap_end=(0, 0.55, 0), lstride=3)


def strap_path(sign, rows=26, rw=1.9, theta_max=1.15):
    """Return (centres (rows,2)=(y,z), tangent-normals, half-widths)."""
    th = np.linspace(0, theta_max, rows)
    z = sign * (B - 0.05 + rw * np.sin(th))
    y = 0.12 + rw * (1 - np.cos(th))
    nrm_y, nrm_z = -np.cos(th), sign * np.sin(th)
    hw = np.linspace(0.72, 0.60, rows)
    return np.stack([y, z], 1), np.stack([nrm_y, nrm_z], 1), hw


def _strap(sign):
    c, n, hw = strap_path(sign)
    th = 0.10
    rings = []
    for (y, z), (ny, nz), w in zip(c, n, hw):
        pts = []
        for sx, so in ((-1, 1), (1, 1), (1, -1), (-1, -1)):
            pts.append((sx * w, y + ny * th * so, z + nz * th * so))
        rings.append(np.array(pts))
    return loft(rings, lstride=1), c[-1]


def _buckle(end_yz):
    y, z = end_yz
    parts = [box(1.5, 0.09, 0.09, (0, y, z - 0.12)), box(1.5, 0.09, 0.09, (0, y, z - 0.62)),
             box(0.09, 0.09, 0.6, (-0.70, y, z - 0.37)), box(0.09, 0.09, 0.6, (0.70, y, z - 0.37))]
    return Mesh.merge(parts)


def build_watch():
    parts = []
    parts.append(Part("frame", _case(), (0.35, 0.85, 1.0), "shell", (0, 0, 0), 0.14, 0.95))
    parts.append(Part("glass", _glass(), (0.55, 0.85, 1.0), "shell", (0, -2.0, 0), 0.07, 0.55))
    parts.append(Part("back", _back(), (0.30, 0.80, 1.0), "shell", (0, 1.6, 0), 0.14, 0.8))

    sensor = Mesh.merge([cylinder(0.78, 0.10, 28, "y", (0, 0.60, 0))] +
                        [cylinder(0.11, 0.08, 10, "y", (0.38 * np.cos(a), 0.66, 0.38 * np.sin(a)))
                         for a in np.radians([45, 135, 225, 315])])
    parts.append(Part("hr_sensor", sensor, (0.35, 1.0, 0.85), "shell", (0, 2.6, 0), 0.2, 1.0))

    crown = cylinder(0.32, 0.42, 20, "x", (A + 0.14, -0.05, 0.75), ridges=5)
    button = box(0.14, 0.40, 0.75, (A + 0.05, 0.0, -0.45))
    parts.append(Part("crown", crown, (0.8, 0.95, 1.0), "shell", (1.8, 0, 0), 0.2, 1.0))
    parts.append(Part("button", button, (0.8, 0.95, 1.0), "shell", (1.8, 0, -0.4), 0.2, 1.0))
    mic = Mesh.merge([cylinder(0.05, 0.1, 8, "x", (-A - 0.01, 0.0, z)) for z in (0.3, 0.5, 0.7)])
    parts.append(Part("mic", mic, (0.8, 0.95, 1.0), "shell", (-1.6, 0, 0), 0.2, 1.0))

    lugs = Mesh.merge([box(1.5, 0.42, 0.5, (0, 0.10, B - 0.12)), box(1.5, 0.42, 0.5, (0, 0.10, -B + 0.12))])
    parts.append(Part("lugs", lugs, (0.55, 0.9, 1.0), "shell", (0, 0.8, 0), 0.2, 0.9))

    for name, sign in (("strap_top", 1), ("strap_bottom", -1)):
        m, end = _strap(sign)
        if sign < 0:
            m = Mesh.merge([m, _buckle(end)])
        parts.append(Part(name, m, (0.10, 0.50, 1.0), "shell", (0, 0.5, 2.6 * sign), 0.2, 0.9))

    # ---- internals (visible in X-ray) ----------------------------------
    parts.append(Part("battery", box(2.3, 0.24, 1.7, (0, 0.20, -0.75)), (1.0, 0.72, 0.2),
                      "internal", (0, 1.2, -0.3), 0.3, 1.0))
    parts.append(Part("pcb", box(2.3, 0.06, 1.35, (0, 0.0, 0.85)), (0.2, 1.0, 0.55),
                      "internal", (0, 0.5, 0.3), 0.3, 1.0))
    chips = Mesh.merge([box(0.65, 0.10, 0.65, (-0.2, -0.07, 1.0)), box(0.35, 0.08, 0.35, (0.7, -0.06, 1.2)),
                        box(0.3, 0.08, 0.3, (0.7, -0.06, 0.6)), box(0.4, 0.08, 0.25, (-0.85, -0.06, 0.45))])
    parts.append(Part("soc", chips, (0.8, 1.0, 1.0), "internal", (0, -0.4, 0.5), 0.35, 1.0))
    parts.append(Part("haptic", cylinder(0.38, 0.22, 20, "y", (0.8, 0.05, -1.35)), (1.0, 0.3, 0.85),
                      "internal", (0.7, 0.9, -0.6), 0.3, 1.0))
    parts.append(Part("speaker", cylinder(0.28, 0.14, 16, "y", (-0.85, 0.05, -1.35)), (0.6, 0.6, 1.0),
                      "internal", (-0.7, 0.9, -0.6), 0.3, 1.0))
    ant = loft([ring3(rrect(A - 0.14, B - 0.14, R - 0.14, ARC, SUB), 0.10),
                ring3(rrect(A - 0.19, B - 0.19, R - 0.19, ARC, SUB), 0.10)], lstride=6)
    parts.append(Part("antenna", ant, (0.4, 1.0, 0.4), "internal", (0, 0.7, 0), 0.25, 1.0))
    parts.append(Part("flex", box(0.8, 0.02, 0.45, (0, -0.28, -1.4)), (1.0, 0.8, 0.3),
                      "internal", (0, -0.9, 0), 0.3, 1.0))
    return parts


def label_anchors():
    """Anchor points (watch-local) for floating-label connection lines."""
    return np.array([[-1.0, -0.5, 1.2], [1.0, -0.5, 1.2], [-1.3, 0.0, 0.0],
                     [1.7, 0.0, -0.3], [-1.0, -0.5, -1.3], [1.0, -0.5, -1.4]], np.float32)


def outline_ring(y, inset=0.02):
    """Closed outline (n,3) around the case for light-pulse effects."""
    return ring3(rrect(A - inset, B - inset, R - inset, ARC, SUB), y).astype(np.float32)
