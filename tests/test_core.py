"""Unit tests for the Panda3D-free modules.  Run:  python -m pytest -q"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from holowatch import config as C
from holowatch.mesh import Mesh, box, cylinder, rrect, loft, ring3
from holowatch.watch_model import build_watch, screen_half_size, outline_ring, label_anchors
from holowatch.particles import ParticleField, EdgeRunners, DataStreams, label_links
from holowatch.telemetry import Telemetry
from holowatch import timeline
from holowatch.screen import WatchScreen, PAGES, W, H


def test_meshes_are_valid():
    parts = build_watch()
    names = {p.name for p in parts}
    for need in ("frame", "glass", "back", "crown", "strap_top", "strap_bottom", "battery", "pcb"):
        assert need in names
    for p in parts:
        m = p.mesh
        assert len(m.verts) > 0 and len(m.tris) > 0 and len(m.lines) > 0
        assert m.tris.max() < len(m.verts) and m.lines.max() < len(m.verts)
        assert np.isfinite(m.verts).all()


def test_watch_proportions():
    shell = Mesh.merge([p.mesh for p in build_watch() if p.kind == "shell"])
    lo, hi = shell.bounds()
    assert abs(hi[0] - lo[0]) > 2 * C.CASE_HALF_W          # crown sticks out
    assert (hi[2] - lo[2]) > 2 * C.CASE_HALF_H + 3         # straps extend
    assert lo[1] < -C.CASE_HALF_T                          # glass dome is in front (-y)
    hw, hh = screen_half_size()
    assert 0.78 < (hw / hh) / (W / H) < 1.22               # screen texture matches aspect


def test_internals_fit_inside_case():
    for p in build_watch():
        if p.kind == "internal":
            lo, hi = p.mesh.bounds()
            assert abs(lo[0]) <= C.CASE_HALF_W and abs(hi[0]) <= C.CASE_HALF_W
            assert abs(lo[2]) <= C.CASE_HALF_H and abs(hi[2]) <= C.CASE_HALF_H
            assert -C.CASE_HALF_T < lo[1] and hi[1] < C.CASE_HALF_T + 0.2


def test_sampling():
    rng = np.random.default_rng(0)
    m = box(1, 1, 1)
    s = m.sample_surface(500, rng)
    assert s.shape == (500, 3) and np.abs(s).max() <= 0.5001
    assert m.sample_edges(100, rng).shape == (100, 3)


def test_rrect_topology_constant():
    assert len(rrect(1.7, 2.0, 0.95)) == len(rrect(1.3, 1.6, 0.6))


def test_particles_form_and_scatter():
    rng = np.random.default_rng(1)
    targets = rng.uniform(-1, 1, (300, 3)).astype(np.float32)
    pf = ParticleField(targets, n_ambient=50)
    mat = np.eye(4, dtype=np.float32)
    pos0, col0 = pf.update(0.016, 0.0, 0.0, mat)
    pos1, col1 = pf.update(0.016, 1.0, 1.0, mat)
    assert pos0.shape == (350, 3) and col0.shape == (350, 4)
    assert np.allclose(pos1[:300], targets, atol=0.06)      # fully formed on the target
    assert np.linalg.norm(pos0[:300] - targets, axis=1).mean() > 2.0   # scattered at form=0
    assert np.isfinite(pos1).all() and np.isfinite(col1).all()
    # settled particles can be hidden by the particle toggle
    _, col_off = pf.update(0.016, 1.0, 1.0, mat, settled_alpha=0.0, ambient_alpha=0.0)
    assert col_off[:, 3].max() == 0.0


def test_effect_arrays_shapes():
    mat = np.eye(4, dtype=np.float32)
    er = EdgeRunners([outline_ring(-0.4), outline_ring(0.4)], 2, 18)
    p, c = er.update(0.016, mat)
    assert p.shape == (er.total, 3) and c.shape == (er.total, 4)
    ds = DataStreams()
    p, c = ds.update(0.016, 0.5)
    assert p.shape == (ds.total, 3) and c.shape == (ds.total, 4) and ds.total % 2 == 0
    LABEL_POS = C.LABEL_POS
    lp, lc, dp, dc = label_links(label_anchors(), np.array(LABEL_POS), mat, 1.0, 0.3)
    assert lp.shape == (24, 3) and lc.shape == (24, 4) and dp.shape == (12, 3)


def test_telemetry_ranges_and_ecg():
    t = Telemetry()
    for _ in range(600):
        t.update(1 / 60)
    assert 60 <= t.bpm <= 95 and 95 <= t.spo2_i <= 100
    assert t.steps_i > 6245 and t.battery_i <= 87
    assert t.ecg.max() > 0.6 and t.ecg.min() < 0.0 and len(t.ecg) == 240
    assert 0.0 <= t.beat <= 1.0
    assert len(t.workout_str()) == 8


def test_timeline_is_monotonic_and_continuous():
    prev = None
    for i in range(0, 1700):
        lv = timeline.levels(i / 100)
        for k in ("platform", "rings", "beams", "form", "wire", "face", "screen", "ui"):
            assert 0.0 <= lv[k] <= 1.0
        if prev:
            for k in ("form", "wire", "face", "screen"):
                assert lv[k] >= prev[k] - 1e-9
        prev = lv
    end, steady = timeline.levels(timeline.INTRO_DURATION), timeline.steady_levels(1.0)
    for k in ("platform", "rings", "beams", "form", "wire", "face", "screen", "ui"):
        assert abs(end[k] - steady[k]) < 1e-6, k
    assert timeline.levels(0.0)["platform"] == 0.0 and timeline.levels(0.0)["form"] == 0.0
    off = timeline.steady_levels(0.0)
    assert off["form"] == 0 and off["face"] == 0 and off["screen"] == 0


def test_screens_render_and_taps():
    tel, scr = Telemetry(), WatchScreen()
    events = []
    scr.on_event = events.append
    for _ in range(30):
        tel.update(1 / 30)
    for i in range(len(PAGES)):
        scr.set_page(i)
        scr.update(0.5)
        img = scr.render(tel)
        assert img.size == (W, H) and img.mode == "RGBA"
        a = np.asarray(img)[..., 3]
        assert a[H // 2, W // 2] > 200 and a[0, 0] < 20     # rounded corner is transparent
    # nav tap switches page
    scr.set_page(0)
    scr.render(tel)
    nav = dict((n, r) for n, r in scr.hits)["nav3"]
    assert scr.tap((nav[0] + nav[2]) / 2, (nav[1] + nav[3]) / 2) and scr.page == 3
    # SOS state machine
    scr.set_page(4)
    scr.render(tel)
    assert scr.tap(144, 138) and scr.sos_state == "counting"
    for _ in range(40):
        scr.update(0.1)
    assert scr.sos_state == "active"
    scr.render(tel)
    assert scr.tap(144, 138) and scr.sos_state == "idle"
    # power-on wipe: fully dark at power 0
    assert np.asarray(scr.render(tel, power=0.0))[..., 3][H // 2, W // 2] == 0


if __name__ == "__main__":      # works without pytest
    import traceback
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception:
                failed += 1
                print("FAIL", name)
                traceback.print_exc()
    sys.exit(1 if failed else 0)
