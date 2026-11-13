"""Panda3D scene objects: watch rig, projection platform, scanners, environment,
floating labels.  All materials are fixed-function (unlit, additive) so the
look is reliable on any GPU / driver (no custom shaders)."""
from __future__ import annotations
import math
import numpy as np
from panda3d.core import (CardMaker, TextNode, NodePath, Texture, TransparencyAttrib,
                          ColorBlendAttrib, TextureStage)

from . import config as C
from .gfx import make_geom_node, holo_style, radial_glow_texture
from .watch_model import build_watch, screen_half_size, SCREEN_Y


# ============================================================ geometry makers
def _colored(name, verts, tris=None, lines=None, colors=None):
    return make_geom_node(name, np.asarray(verts, np.float32),
                          None if tris is None else np.asarray(tris, np.int32),
                          None if lines is None else np.asarray(lines, np.int32),
                          np.asarray(colors, np.float32))


def circle_node(name, radius, segs=96, dash=0, color=C.CYAN, alpha=1.0, z=0.0):
    t = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    v = np.stack([radius * np.cos(t), radius * np.sin(t), np.full(segs, z)], 1)
    lines = [(i, (i + 1) % segs) for i in range(segs) if not dash or (i // dash) % 2 == 0]
    col = np.tile((*color, alpha), (segs, 1))
    return _colored(name, v, lines=lines, colors=col)


def ticks_node(name, radius, n, length, color=C.CYAN, alpha=1.0, every_long=6):
    v, ln = [], []
    for i in range(n):
        a = 2 * np.pi * i / n
        L = length * (2.0 if i % every_long == 0 else 1.0)
        v += [(radius * np.cos(a), radius * np.sin(a), 0), ((radius + L) * np.cos(a), (radius + L) * np.sin(a), 0)]
        ln.append((2 * i, 2 * i + 1))
    return _colored(name, v, lines=ln, colors=np.tile((*color, alpha), (len(v), 1)))


def arc_node(name, radius, a0, a1, color, alpha=1.0, segs=48, plane="xz"):
    t = np.linspace(np.radians(a0), np.radians(a1), segs)
    if plane == "xz":
        v = np.stack([radius * np.cos(t), np.zeros(segs), radius * np.sin(t)], 1)
    else:
        v = np.stack([radius * np.cos(t), radius * np.sin(t), np.zeros(segs)], 1)
    return _colored(name, v, lines=[(i, i + 1) for i in range(segs - 1)],
                    colors=np.tile((*color, alpha), (segs, 1)))


def annulus_node(name, r0, r1, segs=96, color=C.CYAN, a0=0.2, a1=0.2):
    t = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    v = np.vstack([np.stack([r0 * c, r0 * s, np.zeros(segs)], 1), np.stack([r1 * c, r1 * s, np.zeros(segs)], 1)])
    tris = []
    for i in range(segs):
        j = (i + 1) % segs
        tris += [(i, j, segs + j), (i, segs + j, segs + i)]
    col = np.vstack([np.tile((*color, a0), (segs, 1)), np.tile((*color, a1), (segs, 1))])
    return _colored(name, v, tris=tris, colors=col)


def disc_node(name, radius, segs=64, rings=10, color=C.BLUE, a_center=0.5, a_edge=0.0):
    v, col, tris = [(0, 0, 0)], [(*color, a_center)], []
    for r in range(1, rings + 1):
        f = r / rings
        for i in range(segs):
            a = 2 * np.pi * i / segs
            v.append((radius * f * np.cos(a), radius * f * np.sin(a), 0))
            col.append((*color, a_center + (a_edge - a_center) * f))
    for i in range(segs):
        tris.append((0, 1 + i, 1 + (i + 1) % segs))
    for r in range(1, rings):
        b0, b1 = 1 + (r - 1) * segs, 1 + r * segs
        for i in range(segs):
            j = (i + 1) % segs
            tris += [(b0 + i, b0 + j, b1 + j), (b0 + i, b1 + j, b1 + i)]
    return _colored(name, v, tris=tris, colors=col)


def cone_node(name, r0, r1, height, segs=48, color=C.CYAN, a0=0.20, a1=0.0):
    v, col, tris = [], [], []
    for i in range(segs):
        a = 2 * np.pi * i / segs
        v += [(r0 * np.cos(a), r0 * np.sin(a), 0), (r1 * np.cos(a), r1 * np.sin(a), height)]
        col += [(*color, a0), (*color, a1)]
    for i in range(segs):
        j = (i + 1) % segs
        tris += [(2 * i, 2 * j, 2 * j + 1), (2 * i, 2 * j + 1, 2 * i + 1)]
    return _colored(name, v, tris=tris, colors=col)


def beams_node(name, n=28, seed=2):
    rng = np.random.default_rng(seed)
    v, col, ln = [], [], []
    for i in range(n):
        r, a, h = rng.uniform(1.0, 4.8), rng.uniform(0, 2 * np.pi, ), rng.uniform(3.5, 9.5)
        v += [(r * np.cos(a), r * np.sin(a), 0), (r * np.cos(a), r * np.sin(a), h)]
        col += [(0.3, 0.9, 1.0, 0.9), (0.1, 0.5, 1.0, 0.0)]
        ln.append((2 * i, 2 * i + 1))
    return _colored(name, v, lines=ln, colors=col)


def _add(parent, node, order, thickness=None, additive=True):
    n = parent.attachNewNode(node)
    holo_style(n, order, additive)
    if thickness:
        n.setRenderModeThickness(thickness)
    return n


# ================================================================= watch rig
class WatchRig:
    LAYERS = (("faces", 10), ("halo", 11), ("edge", 12))

    def __init__(self, parent):
        self.root = parent.attachNewNode("watch")
        self.parts = []
        self._wire_mode = None
        for spec in build_watch():
            pn = self.root.attachNewNode(spec.name)
            m = spec.mesh
            faces = pn.attachNewNode(make_geom_node(spec.name + "_f", m.verts, tris=m.tris))
            ln_node = make_geom_node(spec.name + "_l", m.verts, lines=m.lines)
            halo, edge = pn.attachNewNode(ln_node), pn.attachNewNode(ln_node)
            for n, order in zip((faces, halo, edge), (10, 11, 12)):
                n.setColor(*spec.color, 1.0)
                holo_style(n, order)
            halo.setRenderModeThickness(5.0)
            edge.setRenderModeThickness(1.6)
            self.parts.append({"spec": spec, "np": pn, "faces": faces, "halo": halo, "edge": edge})
        self._build_screen()

    def _build_screen(self):
        hw, hh = screen_half_size()
        self.screen_half = (hw, hh)
        cm = CardMaker("screen")
        cm.setFrame(-hw, hw, -hh, hh)
        self.screen_np = self.root.attachNewNode(cm.generate())
        self.screen_np.setY(SCREEN_Y)
        self.screen_np.setTransparency(TransparencyAttrib.MAlpha)
        self.screen_np.setLightOff()
        self.screen_np.setTwoSided(False)
        self.screen_np.setDepthWrite(False)
        self.screen_np.setBin("fixed", 20)
        # soft illumination halo behind the screen (selected glow)
        cm2 = CardMaker("screen_glow")
        cm2.setFrame(-hw - 0.25, hw + 0.25, -hh - 0.25, hh + 0.25)
        self.glow_np = self.root.attachNewNode(cm2.generate())
        self.glow_np.setY(SCREEN_Y + 0.02)
        self.glow_np.setTexture(radial_glow_texture(128, (0.1, 0.8, 1.0), 0.9))
        holo_style(self.glow_np, 19, two_sided=False)
        self.glow_np.setColorScale(1, 1, 1, 0)

    def set_screen_texture(self, tex):
        self.screen_np.setTexture(tex)

    def apply(self, face, wire, bright, xray, explode, wireframe, t):
        """face/wire: reveal levels 0..1; bright: intensity; xray/explode: 0..1."""
        if wireframe != self._wire_mode:
            self._wire_mode = wireframe
            for p in self.parts:
                (p["faces"].setRenderModeWireframe if wireframe else p["faces"].setRenderModeFilled)()
        fmult = 2.6 if wireframe else 1.0
        for p in self.parts:
            s = p["spec"]
            if s.kind == "internal":
                vis = xray * wire
                if vis < 0.01:
                    p["np"].hide()
                    continue
                p["np"].show()
                fa, ea, ha = vis * s.face_alpha, vis * s.edge_alpha, vis * 0.3
            else:
                shell = 1.0 - 0.72 * xray
                fa = face * s.face_alpha * shell * (0.25 if wireframe else 1.0) * fmult
                ea = wire * s.edge_alpha * (1.0 - 0.45 * xray)
                ha = wire * 0.20 * (1.0 - 0.5 * xray)
            p["faces"].setColorScale(bright, bright, bright, fa)
            p["halo"].setColorScale(bright, bright, bright, ha)
            p["edge"].setColorScale(bright, bright, bright, ea)
            ex = s.explode
            p["np"].setPos(ex[0] * explode, ex[1] * explode, ex[2] * explode)

    def set_screen_level(self, level, bright, glow):
        self.screen_np.setColorScale(1, 1, 1, level * min(1.0, 0.55 + 0.45 * bright))
        self.glow_np.setColorScale(0.5, 0.9, 1, glow * level * 0.9)


# ============================================================= projection base
class Platform:
    def __init__(self, parent):
        self.root = parent.attachNewNode("platform")
        self.root.setPos(0, 0, C.PLATFORM_Z)
        r = self.root
        self.disc = _add(r, disc_node("disc", 5.6, color=C.BLUE, a_center=0.55, a_edge=0.0), 3)
        self.flash = _add(r, disc_node("flash", 4.0, color=(0.7, 0.95, 1.0), a_center=1.0, a_edge=0.0), 4)
        self.band = _add(r, annulus_node("band", 4.85, 5.2, color=C.CYAN, a0=0.45, a1=0.1), 4)
        self.cone = _add(r, cone_node("cone", 3.6, 2.3, 8.0, a0=0.22), 2)
        # rotating ring family: (node, rpm-ish speed deg/s, base alpha)
        self.rings = []
        for name, node, spd, al in [
            ("r_ticks", ticks_node("t", 5.35, 120, 0.12, C.CYAN, 0.9), 14, 0.9),
            ("r_dash", circle_node("d", 4.35, 120, dash=4, color=C.CYAN), -22, 0.9),
            ("r_mid", circle_node("m", 3.45, 96, dash=16, color=C.ICE), 30, 0.8),
            ("r_in", ticks_node("i", 2.3, 36, 0.18, C.ICE, 0.9, 3), -45, 0.8),
            ("r_core", circle_node("c", 1.8, 64, color=C.CYAN), 0, 0.9),
        ]:
            holder = r.attachNewNode(name)
            _add(holder, node, 5, thickness=1.6)
            self.rings.append([holder, spd, al])
        self.pulse = r.attachNewNode("pulse")
        _add(self.pulse, circle_node("p", 1.0, 96, color=(0.8, 1, 1)), 6, thickness=2.4)
        _add(self.pulse, annulus_node("pb", 0.93, 1.0, color=C.CYAN, a0=0.0, a1=0.6), 6)
        self.beams = _add(r, beams_node("beams"), 7, thickness=2.0)
        self.beams.setColorScale(1, 1, 1, 0)
        self._next_pulse = 6.0

    def update(self, dt, t, lv, bright, steady_pulse=True):
        a = lv["platform"] * bright
        self.root.setScale(lv["platform_scale"])
        self.disc.setColorScale(1, 1, 1, a * (0.6 + 0.4 * lv["rings"]))
        self.band.setColorScale(1, 1, 1, a * (0.4 + 0.6 * lv["rings"]))
        self.flash.setColorScale(1, 1, 1, lv["flash"])
        self.cone.setColorScale(1, 1, 1, lv["form"] * bright * (0.8 + 0.2 * math.sin(t * 5)))
        for holder, spd, al in self.rings:
            holder.setH(holder.getH() + spd * dt * (0.4 + 0.6 * lv["rings"]))
            holder.setColorScale(1, 1, 1, lv["rings"] * al * bright)
        # energy pulse ring (startup burst, then a periodic gentle pulse)
        p = lv["pulse"]
        if lv["done"] and steady_pulse and lv["form"] > 0.5:
            self._next_pulse -= dt
            if self._next_pulse < 0:
                self._next_pulse = 5.0
                self._pulse_t = 0.0
            if hasattr(self, "_pulse_t"):
                self._pulse_t += dt
                p = min(1.0, self._pulse_t / 2.2)
                if p >= 1.0:
                    del self._pulse_t
                    p = 0.0
        if p > 0:
            self.pulse.show()
            self.pulse.setScale(0.5 + 5.5 * p)
            self.pulse.setColorScale(1, 1, 1, (1 - p) * bright)
        else:
            self.pulse.hide()
        self.beams.setSz(max(0.001, lv["beams"]))
        self.beams.setColorScale(1, 1, 1, lv["beams"] * bright * (0.7 + 0.3 * math.sin(t * 9)))


class Scanner:
    """Horizontal scan ring sweeping up/down + fine scan-line sheet."""

    def __init__(self, parent):
        self.ring = parent.attachNewNode("scan_ring")
        for i in range(5):
            _add(self.ring, circle_node("s", 3.6, 96, color=C.ICE, alpha=1.0, z=-0.07 * i), 8,
                 thickness=2.0 if i == 0 else 1.0).setColorScale(1, 1, 1, 1.0 - i * 0.2)
        self.ring_fill = _add(self.ring, disc_node("sf", 3.6, 48, 4, color=C.CYAN, a_center=0.0, a_edge=0.18), 8)
        cm = CardMaker("sheet")
        cm.setFrame(-4.2, 4.2, -0.9, 0.0)
        self.sheet = parent.attachNewNode(cm.generate())
        self.sheet.setPos(0, -1.2, 0)
        sheet_tex = np.zeros((32, 4, 4), np.uint8)
        sheet_tex[:, :, 0], sheet_tex[:, :, 1], sheet_tex[:, :, 2] = 40, 200, 255
        sheet_tex[:, :, 3] = np.linspace(120, 0, 32).astype(np.uint8)[:, None]
        sheet_tex[0, :, 3] = 255  # bright leading edge (row 0 = top of the card)
        from .gfx import texture_from_rgba
        self.sheet.setTexture(texture_from_rgba("sheet", sheet_tex))
        holo_style(self.sheet, 9, two_sided=True)
        self.t = 0.0

    def update(self, dt, enabled, level, bright):
        self.t += dt
        if not enabled or level < 0.01:
            self.ring.hide()
            self.sheet.hide()
            return
        self.ring.show()
        self.sheet.show()
        k = (self.t / 4.0) % 1.0
        tri = 1 - abs(2 * k - 1)
        self.ring.setPos(0, 0, C.WATCH_Z - 3.8 + tri * 7.6)
        self.ring.setColorScale(1, 1, 1, level * bright * 0.9)
        s = (self.t / 3.2) % 1.0
        self.sheet.setZ(C.WATCH_Z - 3.8 + s * 8.0)
        self.sheet.setColorScale(1, 1, 1, level * bright * 0.6 * math.sin(math.pi * s))


class HealthHud:
    """Rotating holographic health-indicator rings behind the watch."""

    def __init__(self, parent):
        self.root = parent.attachNewNode("hud")
        self.root.setPos(0, 2.0, C.WATCH_Z)
        self.arcs = []
        spec = [(4.1, C.GREEN, 0.76 / 1.2, 22), (4.5, C.CYAN, 0.98, -16), (4.9, C.AMBER, 0.87, 11)]
        for r, col, frac, spd in spec:
            h = self.root.attachNewNode("arc")
            _add(h, arc_node("a", r, 0, 330 * frac, col, 1.0), 5, thickness=3.0)
            _add(h, arc_node("b", r, 330 * frac + 8, 350, col, 0.25), 5, thickness=1.2)
            _add(h, arc_node("c", r - 0.12, 0, 360, col, 0.12, 90), 5, thickness=1.0)
            self.arcs.append((h, spd))
        self.t = 0.0

    def update(self, dt, level, bright):
        for h, spd in self.arcs:
            h.setR(h.getR() + spd * dt)
        self.root.setColorScale(1, 1, 1, level * bright * 0.8)


# ============================================================== environment
class Environment:
    def __init__(self, render, render2d):
        # floor grid
        v, col, ln = [], [], []
        n, step, ext = 0, 2.0, 24.0
        for g in np.arange(-ext, ext + 0.1, step):
            for (x0, y0, x1, y1) in ((g, -ext, g, ext), (-ext, g, ext, g)):
                for (x, y) in ((x0, y0), (x1, y1)):
                    d = math.hypot(x, y)
                    v.append((x, y, C.PLATFORM_Z - 0.3))
                    col.append((0.1, 0.5, 1.0, max(0.0, 0.5 * (1 - d / (ext * 1.2)))))
                ln.append((2 * n, 2 * n + 1))
                n += 1
        self.grid = _add(render, _colored("grid", v, lines=ln, colors=col), 1)
        # backdrop glow
        cm = CardMaker("backdrop")
        cm.setFrame(-26, 26, -18, 18)
        self.back = render.attachNewNode(cm.generate())
        self.back.setPos(0, 18, 0)
        self.back.setTexture(radial_glow_texture(256, (0.0, 0.30, 0.75), 2.0))
        holo_style(self.back, 0, two_sided=True)
        self.back.setColorScale(1, 1, 1, 0)
        # CRT-style scanline overlay
        from .gfx import scanline_texture
        cm = CardMaker("scan_overlay")
        cm.setFrame(-1, 1, -1, 1)
        self.overlay = render2d.attachNewNode(cm.generate())
        self.overlay.setTexture(scanline_texture())
        self.overlay.setTexScale(TextureStage.getDefault(), 1, 3)
        self.overlay.setTransparency(TransparencyAttrib.MAlpha)
        self.overlay.setBin("fixed", 90)
        self.overlay.setColorScale(1, 1, 1, 0)

    def update(self, lv, bright, scan_on):
        self.back.setColorScale(1, 1, 1, (0.25 + 0.75 * lv["platform"]) * (0.5 + 0.5 * bright) * 0.9)
        self.grid.setColorScale(1, 1, 1, lv["platform"] * 0.8)
        self.overlay.setColorScale(1, 1, 1, lv["platform"] if scan_on else 0.0)


# ================================================================== labels
LABEL_POS = C.LABEL_POS


class FloatingLabels:
    def __init__(self, parent):
        self.root = parent.attachNewNode("labels")
        self.nodes = []
        for i, pos in enumerate(LABEL_POS):
            tn = TextNode(f"label{i}")
            tn.setAlign(TextNode.ACenter)
            tn.setTextColor(0.45, 0.97, 1.0, 1)
            tn.setText("...")
            np_ = self.root.attachNewNode(tn)
            np_.setPos(*pos)
            np_.setScale(0.40)
            np_.setBillboardPointEye()
            np_.setLightOff()
            np_.setDepthWrite(False)
            np_.setTransparency(TransparencyAttrib.MAlpha)
            np_.setBin("fixed", 40)
            self.nodes.append((tn, np_))
        self.world_positions = np.array(LABEL_POS, np.float32)

    def set_texts(self, texts):
        for (tn, _), s in zip(self.nodes, texts):
            tn.setText(s)

    def set_level(self, level, bright):
        self.root.setColorScale(1, 1, 1, level * min(1.0, bright))
