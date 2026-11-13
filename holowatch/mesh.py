"""Pure-NumPy mesh toolkit (no Panda3D import so it can be unit-tested anywhere).

A Mesh holds vertices, triangles (translucent faces) and line pairs (neon
edge layer).  Coordinates: x right, y depth (+y = back of watch), z up.
"""
from __future__ import annotations
import numpy as np


class Mesh:
    def __init__(self, verts=None, tris=None, lines=None):
        self.verts = (np.zeros((0, 3), np.float32) if verts is None
                      else np.asarray(verts, np.float32).reshape(-1, 3))
        self.tris = (np.zeros((0, 3), np.int32) if tris is None
                     else np.asarray(tris, np.int32).reshape(-1, 3))
        self.lines = (np.zeros((0, 2), np.int32) if lines is None
                      else np.asarray(lines, np.int32).reshape(-1, 2))

    def transformed(self, scale=1.0, offset=(0, 0, 0), rot=None) -> "Mesh":
        v = self.verts.astype(np.float64) * scale
        if rot is not None:
            v = v @ np.asarray(rot, np.float64).T
        v = v + np.asarray(offset, np.float64)
        return Mesh(v, self.tris, self.lines)

    @staticmethod
    def merge(meshes) -> "Mesh":
        vs, ts, ls, off = [], [], [], 0
        for m in meshes:
            vs.append(m.verts)
            ts.append(m.tris + off)
            ls.append(m.lines + off)
            off += len(m.verts)
        if not vs:
            return Mesh()
        return Mesh(np.vstack(vs), np.vstack(ts), np.vstack(ls))

    def bounds(self):
        return self.verts.min(axis=0), self.verts.max(axis=0)

    def sample_surface(self, n, rng):
        """Area-weighted random points on the triangle surface."""
        if len(self.tris) == 0:
            return np.zeros((0, 3), np.float32)
        a, b, c = (self.verts[self.tris[:, i]] for i in range(3))
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        idx = rng.choice(len(self.tris), size=n, p=area / area.sum())
        u, v = rng.random(n), rng.random(n)
        flip = u + v > 1
        u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
        pts = a[idx] + (b[idx] - a[idx]) * u[:, None] + (c[idx] - a[idx]) * v[:, None]
        return pts.astype(np.float32)

    def sample_edges(self, n, rng):
        """Length-weighted random points along the line set."""
        p, q = self.verts[self.lines[:, 0]], self.verts[self.lines[:, 1]]
        ln = np.linalg.norm(q - p, axis=1)
        idx = rng.choice(len(self.lines), size=n, p=ln / ln.sum())
        t = rng.random(n)[:, None]
        return (p[idx] + (q[idx] - p[idx]) * t).astype(np.float32)


def rot_x(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rrect(a, b, r, arc=12, sub=3):
    """Rounded-rectangle outline (n,2) in (x,z), CCW.  Topology depends only on
    (arc, sub), so rings of different size can be lofted together."""
    r = max(min(r, a - 1e-3, b - 1e-3), 1e-3)
    corners = [(a - r, b - r, 0), (-(a - r), b - r, 90),
               (-(a - r), -(b - r), 180), (a - r, -(b - r), 270)]
    groups = []
    for cx, cz, st in corners:
        ang = np.radians(st + 90.0 * np.arange(arc + 1) / arc)
        groups.append(np.stack([cx + r * np.cos(ang), cz + r * np.sin(ang)], 1))
    pts = []
    for i, g in enumerate(groups):
        pts.append(g)
        nxt = groups[(i + 1) % 4][0]
        if sub > 1:
            t = (np.arange(1, sub) / sub)[:, None]
            pts.append(g[-1] + (nxt - g[-1]) * t)
    return np.vstack(pts)


def ring3(pts2, y):
    return np.stack([pts2[:, 0], np.full(len(pts2), y), pts2[:, 1]], 1)


def loft(rings, closed=True, cap_end=None, cap_start=None, lstride=2):
    """Skin a list of equal-length rings (each (n,3)); optional centre caps."""
    rings = [np.asarray(r, np.float64) for r in rings]
    n = len(rings[0])
    verts = [np.vstack(rings)]
    tris, lines = [], []
    cols = range(n) if closed else range(n - 1)
    for i in range(len(rings)):
        for j in cols:
            lines.append((i * n + j, i * n + (j + 1) % n))
    for i in range(len(rings) - 1):
        for j in cols:
            j2 = (j + 1) % n
            a, b = i * n + j, i * n + j2
            c, d = (i + 1) * n + j2, (i + 1) * n + j
            tris += [(a, b, c), (a, c, d)]
            if j % lstride == 0:
                lines.append((a, d))
    count = n * len(rings)

    def add_cap(ring_idx, center):
        nonlocal count
        verts.append(np.asarray(center, np.float64).reshape(1, 3))
        ci = count
        count += 1
        base = ring_idx * n
        for j in range(n):
            tris.append((base + j, base + (j + 1) % n, ci))
            if j % max(lstride * 2, 2) == 0:
                lines.append((base + j, ci))

    if cap_end is not None:
        add_cap(len(rings) - 1, cap_end)
    if cap_start is not None:
        add_cap(0, cap_start)
    return Mesh(np.vstack(verts), tris, lines)


def box(sx, sy, sz, center=(0, 0, 0)):
    x, y, z = sx / 2, sy / 2, sz / 2
    v = np.array([[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z],
                  [-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]], float) + center
    f = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 5, 1), (0, 4, 5),
         (1, 6, 2), (1, 5, 6), (2, 7, 3), (2, 6, 7), (3, 4, 0), (3, 7, 4)]
    e = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
         (0, 4), (1, 5), (2, 6), (3, 7)]
    return Mesh(v, f, e)


def cylinder(radius, length, segs=24, axis="z", center=(0, 0, 0), ridges=0):
    """Capped cylinder along the chosen axis; ridges>0 gives a knurled side."""
    ang = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    rings = []
    if ridges:
        for k, z in enumerate(np.linspace(-length / 2, length / 2, ridges * 2 + 1)):
            r = radius if k % 2 == 0 else radius * 0.9
            rings.append(np.stack([r * np.cos(ang), r * np.sin(ang), np.full(segs, z)], 1))
    else:
        for z in (-length / 2, length / 2):
            rings.append(np.stack([radius * np.cos(ang), radius * np.sin(ang),
                                   np.full(segs, z)], 1))
    m = loft(rings, cap_end=(0, 0, length / 2), cap_start=(0, 0, -length / 2), lstride=1)
    rot = {"z": None, "y": rot_x(90), "x": rot_y(90)}[axis]
    return m.transformed(rot=rot, offset=center)
