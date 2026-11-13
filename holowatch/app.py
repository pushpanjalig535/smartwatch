"""Main application: wires the scene, effects, watch screen, dashboard and input."""
from __future__ import annotations
import math
import sys
import random
import numpy as np

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (AntialiasAttrib, Point3, Texture, ClockObject, NodePath)

from . import config as C
from .gfx import DynamicGeom, mat4_to_np
from .mesh import Mesh
from .particles import ParticleField, EdgeRunners, DataStreams, label_links
from .scene import WatchRig, Platform, Scanner, HealthHud, Environment, FloatingLabels
from .screen import WatchScreen, W as SCR_W, H as SCR_H
from .sfx import Sfx
from .telemetry import Telemetry
from .timeline import (levels, steady_levels, caption, INTRO_DURATION, HEALTH_PAGE_TIME,
                       MESSAGE, smooth)
from .ui import Dashboard
from .watch_model import outline_ring, label_anchors, SCREEN_Y, screen_half_size

INSPECT_VIEWS = [(0, 0, "FRONT VIEW"), (90, 0, "LEFT SIDE VIEW"), (180, 0, "BACK VIEW // HEART-RATE SENSOR"),
                 (270, 0, "RIGHT SIDE VIEW // CROWN + BUTTON"), (0, 65, "TOP EDGE // STRAP LUGS"),
                 (0, -65, "BOTTOM EDGE // BUCKLE"), (0, 0, "INSPECTION COMPLETE")]
INSPECT_HOLD = 2.6

INTRO_EVENTS = [(1.0, "hum"), (3.0, "pulse"), (4.2, "whoosh"), (10.6, "beep"), (12.0, "beep")]


class State:
    projection = True
    wireframe = False
    particles = True
    scanning = True
    xray = False
    explode = False
    inspect = False
    paused = False
    brightness = 1.0
    speed = 20.0
    size = 1.0


def _approach(cur, target, step):
    return cur + max(-step, min(step, target - cur))


class HoloApp(ShowBase):
    def __init__(self, skip_intro=False, bloom=False, audio=True):
        ShowBase.__init__(self)
        self.disableMouse()
        self.setBackgroundColor(0.0, 0.008, 0.02)
        self.render.setAntialias(AntialiasAttrib.MAuto)
        self.camLens.setFov(50)
        self.camLens.setNearFar(1.0, 400.0)
        self.setFrameRateMeter(False)

        self.state = State()
        self.lv = levels(0.0)
        self.t = 0.0
        self.proj = 1.0
        self.heading = self.pitch = 0.0
        self.vel_h = self.vel_p = 0.0
        self.cam_dist = self.cam_dist_target = C.CAM_DIST_DEFAULT
        self.dragging = False
        self.last_mouse = (0.0, 0.0)
        self.down_mouse = (0.0, 0.0)
        self.sel_flag = False
        self.sel = 0.0
        self.explode_amt = self.xray_amt = 0.0
        self.inspect_i = 0
        self.inspect_timer = 0.0
        self.glitch_t = 0.0
        self.next_glitch = 8.0
        self.label_timer = 0.0
        self.screen_timer = 0.0
        self.health_set = False
        self.events = list(INTRO_EVENTS)
        self.fps_smooth = 60.0
        self.hud_on = True
        self.filters = None

        self.tel = Telemetry()
        self.screen = WatchScreen()
        self.sfx = Sfx(self.loader) if audio else Sfx.__new__(Sfx)
        if not audio:
            self.sfx.s = {}

        self._build_scene()
        self.ui = Dashboard(self)
        self.screen.on_event = self.log_event
        self._setup_input()
        if bloom:
            self.toggle_bloom()
        if skip_intro:
            self.skip_intro()
        self.log_event("SYSTEM BOOT")
        self.taskMgr.add(self._update, "update")

    # =========================================================== construction
    def _build_scene(self):
        r = self.render
        self.env = Environment(r, self.render2d)
        self.platform = Platform(r)
        self.rig = WatchRig(r)
        self.scanner = Scanner(r)
        self.hud = HealthHud(r)
        self.labels = FloatingLabels(r)

        # glitch "ghost" copy of the whole watch (instanced, tinted)
        self.ghost = r.attachNewNode("ghost")
        self.rig.root.instanceTo(self.ghost)
        self.ghost.setColorScale(1.0, 0.3, 0.75, 0.45)
        self.ghost.hide()

        # screen texture
        self.screen_tex = Texture("watch_screen")
        self.screen_tex.setup2dTexture(SCR_W, SCR_H, Texture.TUnsignedByte, Texture.FRgba8)
        self.screen_tex.setMinfilter(Texture.FTLinear)
        self.screen_tex.setMagfilter(Texture.FTLinear)
        self.rig.set_screen_texture(self.screen_tex)
        self._upload_screen(0.0)

        # particle targets sampled from the actual watch geometry
        rng = np.random.default_rng(21)
        shell = Mesh.merge([p["spec"].mesh for p in self.rig.parts if p["spec"].kind == "shell"])
        hw, hh = screen_half_size()
        scr = np.stack([rng.uniform(-hw, hw, 220), np.full(220, SCREEN_Y), rng.uniform(-hh, hh, 220)], 1)
        targets = np.vstack([shell.sample_surface(900, rng), shell.sample_edges(480, rng), scr]).astype(np.float32)
        self.pf = ParticleField(targets, n_ambient=450)
        self.runners = EdgeRunners([outline_ring(-0.40), outline_ring(0.40, 0.1)], 2, 18)
        self.streams = DataStreams()
        self.g_particles = DynamicGeom("particles", self.pf.total, r, "points", 30, 3.0)
        self.g_runners = DynamicGeom("runners", self.runners.total, r, "points", 31, 4.5)
        self.g_streams = DynamicGeom("streams", self.streams.total, r, "lines", 29, 1.5)
        self.g_links = DynamicGeom("links", 24, r, "lines", 32, 1.3)
        self.g_dots = DynamicGeom("dots", 12, r, "points", 33, 6.0)
        self.anchors = label_anchors()

    def _upload_screen(self, power):
        img = self.screen.render(self.tel, power)
        arr = np.asarray(img)[::-1]
        self.screen_tex.setRamImageAs(np.ascontiguousarray(arr).tobytes(), "RGBA")

    # ================================================================= input
    def _setup_input(self):
        a = self.accept
        a("mouse1", self._mouse_down)
        a("mouse1-up", self._mouse_up)
        a("wheel_up", self._zoom, [-1])
        a("wheel_down", self._zoom, [1])
        keys = {"space": self.toggle_pause, "r": self.reset_view, "p": self.toggle_projection,
                "w": self.toggle_wireframe, "x": self.toggle_xray, "e": self.toggle_explode,
                "i": self.toggle_inspect, "s": self.toggle_scanning, "t": self.toggle_particles,
                "b": self.toggle_bloom, "h": self.toggle_hud, "enter": self.skip_intro,
                "arrow_right": self.screen.next_page, "arrow_left": self.screen.prev_page,
                "escape": sys.exit}
        for k, fn in keys.items():
            a(k, self._act, [fn])
        for i in range(5):
            a(str(i + 1), self._act, [self.screen_page, i])

    def _act(self, fn, *args):
        fn(*args)
        if hasattr(self, "ui"):
            self.ui.sync()

    def _mouse(self):
        if self.mouseWatcherNode.hasMouse():
            m = self.mouseWatcherNode.getMouse()
            return (m.getX(), m.getY())
        return None

    def _mouse_down(self):
        if self.mouseWatcherNode.isOverRegion():
            return
        m = self._mouse()
        if m:
            self.dragging = True
            self.last_mouse = self.down_mouse = m
            self.vel_h = self.vel_p = 0.0

    def _mouse_up(self):
        if not self.dragging:
            return
        self.dragging = False
        m = self._mouse() or self.down_mouse
        if math.hypot(m[0] - self.down_mouse[0], m[1] - self.down_mouse[1]) < 0.012:
            self._click()

    def _zoom(self, d):
        if self.mouseWatcherNode.isOverRegion():
            return
        self.cam_dist_target = min(C.CAM_DIST_MAX, max(C.CAM_DIST_MIN, self.cam_dist_target * (1 + 0.08 * d)))

    def pick_screen(self):
        """Ray-cast the mouse onto the 3D watch screen -> texture pixel or None."""
        if not self.mouseWatcherNode.hasMouse():
            return None
        near, far = Point3(), Point3()
        self.camLens.extrude(self.mouseWatcherNode.getMouse(), near, far)
        sn = self.rig.screen_np
        p1 = sn.getRelativePoint(self.cam, near)
        p2 = sn.getRelativePoint(self.cam, far)
        dy = p2.y - p1.y
        if p1.y >= 0 or abs(dy) < 1e-6:
            return None                      # looking at the back of the screen
        t = -p1.y / dy
        if t < 0:
            return None
        x, z = p1.x + (p2.x - p1.x) * t, p1.z + (p2.z - p1.z) * t
        hw, hh = self.rig.screen_half
        if abs(x) > hw or abs(z) > hh:
            return None
        return ((x + hw) / (2 * hw) * SCR_W, (hh - z) / (2 * hh) * SCR_H)

    def _click(self):
        if self.lv["screen"] < 0.9 or not self.state.projection:
            return
        hit = self.pick_screen()
        if hit is None:
            self.sel_flag = False
            return
        self.sel_flag = True
        self.sel = 1.0
        self.sfx.play("click")
        if self.screen.tap(*hit):
            self.ui.sync()

    # ========================================================== user actions
    def log_event(self, text):
        print("[holo]", text)
        if hasattr(self, "ui"):
            self.ui.log_event(text)
            self.ui.sync()

    def _end_intro(self):
        if self.t < INTRO_DURATION:
            self.skip_intro()

    def skip_intro(self):
        if self.t < INTRO_DURATION:
            self.t = INTRO_DURATION
            self.events = []
            self.proj = 1.0
            if not self.health_set:
                self.health_set = True
                self.screen.page = 1
            self.sfx.start_hum()
            if hasattr(self, "ui"):
                self.log_event("INTRO SKIPPED")

    def toggle_projection(self):
        self._end_intro()
        self.state.projection = not self.state.projection
        self.log_event("PROJECTION " + ("ONLINE" if self.state.projection else "OFFLINE"))
        self.sfx.play("pulse" if self.state.projection else "whoosh", 0.7)
        if not self.state.projection:
            self.sel_flag = False

    def set_brightness(self, v): self.state.brightness = float(v)
    def set_speed(self, v): self.state.speed = float(v)
    def set_size(self, v): self.state.size = float(v)

    def toggle_wireframe(self):
        self.state.wireframe = not self.state.wireframe
        self.log_event("WIREFRAME " + ("ON" if self.state.wireframe else "OFF"))

    def toggle_particles(self):
        self.state.particles = not self.state.particles
        self.log_event("PARTICLE EFFECTS " + ("ON" if self.state.particles else "OFF"))

    def toggle_scanning(self):
        self.state.scanning = not self.state.scanning
        self.log_event("SCANNING " + ("ON" if self.state.scanning else "OFF"))

    def toggle_xray(self):
        self._end_intro()
        self.state.xray = not self.state.xray
        self.log_event("X-RAY MODE " + ("ENGAGED" if self.state.xray else "OFF"))
        self.sfx.play("beep", 0.6)

    def toggle_explode(self):
        self._end_intro()
        self.state.explode = not self.state.explode
        self.log_event("DISASSEMBLY " + ("STARTED" if self.state.explode else "REASSEMBLING"))
        self.sfx.play("whoosh", 0.6)

    def toggle_inspect(self):
        self._end_intro()
        self.state.inspect = not self.state.inspect
        if self.state.inspect:
            self.inspect_i, self.inspect_timer = 0, 0.0
            self.log_event("360 INSPECTION STARTED")
        else:
            self.log_event("INSPECTION ENDED")

    def toggle_pause(self):
        self.state.paused = not self.state.paused
        self.log_event("ROTATION " + ("PAUSED" if self.state.paused else "RESUMED"))

    def toggle_hud(self):
        self.hud_on = not self.hud_on

    def screen_page(self, i):
        self._end_intro()
        self.screen.set_page(i)
        self.sfx.play("click", 0.6)
        if hasattr(self, "ui"):
            self.ui.sync()

    def reset_view(self):
        s = self.state
        self.heading = self.pitch = 0.0
        self.vel_h = self.vel_p = 0.0
        self.cam_dist_target = C.CAM_DIST_DEFAULT
        s.size, s.speed, s.brightness = 1.0, 20.0, 1.0
        s.paused = s.explode = s.xray = s.inspect = False
        self.log_event("CAMERA + WATCH RESET")
        if hasattr(self, "ui"):
            self.ui.sync()

    def toggle_bloom(self):
        """Optional post-process bloom (shader based; off by default)."""
        try:
            if self.filters:
                self.filters.cleanup()
                self.filters = None
                self.log_event("BLOOM OFF")
                return
            from direct.filter.CommonFilters import CommonFilters
            self.filters = CommonFilters(self.win, self.cam)
            ok = self.filters.setBloom(blend=(0, 0, 0, 1), mintrigger=0.25, maxtrigger=0.9,
                                       desat=0.2, intensity=1.3, size="medium")
            if not ok:
                self.filters.cleanup()
                self.filters = None
                self.log_event("BLOOM UNSUPPORTED ON THIS GPU")
            else:
                self.log_event("BLOOM ON")
        except Exception as e:
            self.filters = None
            self.log_event("BLOOM FAILED: " + str(e)[:40])

    # ================================================================= update
    def _update(self, task):
        dt = min(ClockObject.getGlobalClock().getDt(), 0.05)
        self.t += dt
        st = self.state
        self.fps_smooth += (1 / max(dt, 1e-4) - self.fps_smooth) * 0.05

        # ---- levels
        if self.t < INTRO_DURATION:
            lv = levels(self.t)
        else:
            self.proj = _approach(self.proj, 1.0 if st.projection else 0.0, dt * 0.6)
            lv = steady_levels(self.proj)
        self.lv = lv
        bright = st.brightness

        for ev in list(self.events):
            if self.t >= ev[0]:
                self.events.remove(ev)
                self.sfx.start_hum() if ev[1] == "hum" else self.sfx.play(ev[1])
        if not self.health_set and self.t >= HEALTH_PAGE_TIME:
            self.health_set = True
            self.screen.set_page(1)
            self.ui.sync()

        self.tel.update(dt)
        self.screen.update(dt)
        self._update_rotation(dt, lv)

        # animated amounts
        self.explode_amt = _approach(self.explode_amt, 1.0 if st.explode else 0.0, dt * 0.9)
        self.xray_amt = _approach(self.xray_amt, 1.0 if st.xray else 0.0, dt * 1.4)
        ex, xr = smooth(self.explode_amt), smooth(self.xray_amt)

        # ---- watch transform
        hover = C.WATCH_Z + 0.12 * math.sin(self.t * 1.3)
        scale = st.size * (0.9 + 0.1 * lv["face"])
        root = self.rig.root
        root.setPos(0, 0, hover)
        root.setHpr(self.heading, self.pitch, 0)
        root.setScale(scale)

        # glitch / distortion
        self.next_glitch -= dt
        if self.next_glitch <= 0 and lv["face"] > 0.9:
            self.glitch_t = random.uniform(0.12, 0.28)
            self.next_glitch = random.uniform(6, 12)
        if self.glitch_t > 0:
            self.glitch_t -= dt
            jx = random.uniform(-0.18, 0.18)
            root.setX(jx * 0.5)
            self.ghost.setPos(-jx * 2.0, 0.0, 0.0)
            self.ghost.show()
        else:
            self.ghost.hide()

        # ---- apply visuals
        self.rig.apply(lv["face"], lv["wire"], bright, xr, ex, st.wireframe, self.t)
        self.sel = _approach(self.sel, 0.55 if self.sel_flag else 0.0, dt * (0.6 if self.sel_flag else 1.5))
        self.screen.selected = min(1.0, self.sel * 1.8)
        self.rig.set_screen_level(min(1.0, lv["screen"] * 5), bright, self.sel)
        self.screen_timer -= dt
        if lv["screen"] > 0.001 and self.screen_timer <= 0:
            self.screen_timer = 1 / 20
            self._upload_screen(lv["screen"])

        self.env.update(lv, bright, st.scanning)
        self.platform.update(dt, self.t, lv, bright)
        self.scanner.update(dt, st.scanning and lv["form"] > 0.95, lv["wire"], bright)
        self.hud.root.setPos(0, 2.0, hover)
        self.hud.update(dt, lv["screen"] * (1.0 if self.hud_on else 0.0), bright)

        mat = mat4_to_np(root.getMat(self.render))
        settled = (1.0 if st.particles else 0.0) * (1 - 0.8 * ex)
        pos, col = self.pf.update(dt, self.t, lv["form"], mat, settled,
                                  1.0 if st.particles else 0.0, bright)
        self.g_particles.update(pos, col)
        pos, col = self.runners.update(dt, mat, lv["wire"] * bright * (1 - 0.6 * ex))
        self.g_runners.update(pos, col)
        pos, col = self.streams.update(dt, self.t, lv["rings"] * (1.0 if st.particles else 0.35) * bright)
        self.g_streams.update(pos, col)
        lp, lc, dp, dc = label_links(self.anchors, self.labels.world_positions + (0, 0, C.WATCH_Z), mat,
                                     lv["screen"] * bright * (1 - 0.7 * ex), self.t)
        self.g_links.update(lp, lc)
        self.g_dots.update(dp, dc)
        self.labels.set_level(lv["screen"] * (1 - 0.7 * ex), bright)
        self.label_timer -= dt
        if self.label_timer <= 0:
            self.label_timer = 0.25
            t = self.tel
            self.labels.set_texts([f"HEART RATE\n{t.bpm} BPM", f"SpO2\n{t.spo2_i}%", f"BATTERY\n{t.battery_i}%",
                                   f"STEPS\n{t.steps_i:,}", "DISPLAY\nAMOLED  396x484",
                                   "PROJECTION\n" + ("ACTIVE" if st.projection else "OFFLINE")])

        # ---- camera
        self.cam_dist += (self.cam_dist_target - self.cam_dist) * min(1.0, dt * 8)
        el = math.radians(C.CAM_ELEV_DEG)
        d = self.cam_dist
        self.camera.setPos(0, -d * math.cos(el), C.CAM_TARGET_Z + d * math.sin(el))
        self.camera.lookAt(0, 0, C.CAM_TARGET_Z)

        # ---- UI
        cap = caption(self.t) if self.t < INTRO_DURATION else ""
        if st.inspect:
            cap = "INSPECTION // " + INSPECT_VIEWS[min(self.inspect_i, len(INSPECT_VIEWS) - 1)][2]
        n = int(len(MESSAGE) * lv["typed"])
        message = MESSAGE[:n] if lv["message"] > 0.01 else ""
        self.ui.set_alpha(lv["ui"])
        self.ui.update(self.t, self.tel, st, self.fps_smooth, cap, message, lv["message"])
        return task.cont

    def _update_rotation(self, dt, lv):
        st = self.state
        m = self._mouse()
        if self.dragging and m:
            dx, dy = m[0] - self.last_mouse[0], m[1] - self.last_mouse[1]
            self.last_mouse = m
            if st.inspect and (abs(dx) + abs(dy)) > 0.002:
                st.inspect = False
                self.ui.sync()
            self.heading += dx * 220.0
            self.pitch -= dy * 150.0
            self.vel_h = dx * 220.0 / max(dt, 1e-3) * 0.5
            self.vel_p = -dy * 150.0 / max(dt, 1e-3) * 0.5
            return
        if st.inspect:
            self._update_inspect(dt)
            return
        spin = 0.0 if (st.paused or lv["face"] < 0.01) else st.speed * smooth(lv["face"], 0.0, 1.0)
        self.heading += (spin + self.vel_h) * dt
        self.pitch += self.vel_p * dt
        k = math.exp(-3.0 * dt)
        self.vel_h *= k
        self.vel_p *= k
        self.heading %= 360.0
        self.pitch = ((self.pitch + 180) % 360) - 180

    def _update_inspect(self, dt):
        self.inspect_timer += dt
        if self.inspect_timer > INSPECT_HOLD:
            self.inspect_timer = 0.0
            self.inspect_i += 1
            if self.inspect_i >= len(INSPECT_VIEWS):
                self.state.inspect = False
                self.log_event("INSPECTION COMPLETE")
                self.ui.sync()
                return
        th, tp, _ = INSPECT_VIEWS[self.inspect_i]
        k = min(1.0, dt * 3.0)
        self.heading += (((th - self.heading + 180) % 360) - 180) * k
        self.pitch += (((tp - self.pitch + 180) % 360) - 180) * k
