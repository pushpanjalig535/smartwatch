"""Futuristic control dashboard built with Panda3D DirectGui."""
from __future__ import annotations
import time
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectSlider, DGG
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, TransparencyAttrib

CY = (0.0, 0.92, 1.0, 1.0)
DIMC = (0.25, 0.55, 0.65, 1.0)
GRN = (0.2, 1.0, 0.6, 1.0)
RED = (1.0, 0.3, 0.35, 1.0)
AMB = (1.0, 0.75, 0.25, 1.0)
PANEL_W = 0.70

BTN_OFF = ((0.0, 0.14, 0.22, 0.75), (0.0, 0.5, 0.7, 0.95), (0.0, 0.3, 0.42, 0.9), (0.1, 0.1, 0.1, 0.3))
BTN_ON = ((0.0, 0.42, 0.58, 0.9), (0.0, 0.7, 0.9, 1.0), (0.0, 0.52, 0.7, 0.95), (0.1, 0.1, 0.1, 0.3))


def _panel(parent, x, z, w, h, title):
    outer = DirectFrame(parent=parent, frameSize=(0, w, -h, 0), frameColor=(0.0, 0.8, 1.0, 0.55),
                        pos=(x, 0, z), relief=DGG.FLAT)
    DirectFrame(parent=outer, frameSize=(0.004, w - 0.004, -h + 0.004, -0.004),
                frameColor=(0.0, 0.05, 0.10, 0.72), relief=DGG.FLAT)
    DirectFrame(parent=outer, frameSize=(0.01, w - 0.01, -0.062, -0.058), frameColor=(0.0, 0.8, 1.0, 0.7), relief=DGG.FLAT)
    OnscreenText(text=title, parent=outer, pos=(0.025, -0.045), scale=0.034, fg=CY,
                 align=TextNode.ALeft, shadow=(0, 0, 0, 0.8))
    outer.setTransparency(TransparencyAttrib.MAlpha)
    return outer


class Dashboard:
    def __init__(self, app):
        self.app = app
        self.toggles = {}
        self.sliders = {}
        self.root = app.aspect2d.attachNewNode("dashboard")
        TL, TR, BC = app.a2dTopLeft, app.a2dTopRight, app.a2dBottomCenter

        # ------------------------------------------------ top status line
        self.status = OnscreenText(text="HOLOGRAM SYSTEM: ONLINE", parent=app.a2dTopCenter, pos=(0, -0.075),
                                   scale=0.05, fg=CY, shadow=(0, 0, 0, 0.9), mayChange=True)
        self.caption = OnscreenText(text="", parent=app.a2dTopCenter, pos=(0, -0.14), scale=0.034,
                                    fg=(0.6, 0.95, 1.0, 1), mayChange=True)

        # ------------------------------------------------ projection controls
        self.left = _panel(TL, 0.03, -0.03, PANEL_W, 1.02, "PROJECTION CONTROLS")
        z = -0.13
        self._toggle(self.left, "projection", "PROJECTION", z, app.toggle_projection)
        z -= 0.092
        for key, label, lo, hi, setter in (
                ("brightness", "HOLOGRAM BRIGHTNESS", 0.2, 1.6, app.set_brightness),
                ("speed", "ROTATION SPEED", 0.0, 120.0, app.set_speed),
                ("size", "PROJECTION SIZE", 0.5, 1.5, app.set_size)):
            OnscreenText(text=label, parent=self.left, pos=(0.03, z), scale=0.027, fg=DIMC, align=TextNode.ALeft)
            s = DirectSlider(parent=self.left, range=(lo, hi), value=getattr(app.state, key), pageSize=(hi - lo) / 10,
                             frameSize=(-0.31, 0.31, -0.012, 0.012), pos=(PANEL_W / 2, 0, z - 0.04),
                             frameColor=(0.0, 0.3, 0.4, 0.8), thumb_relief=DGG.FLAT,
                             thumb_frameColor=(0.0, 0.95, 1.0, 1.0), thumb_frameSize=(-0.012, 0.012, -0.03, 0.03),
                             command=(lambda k=key, st=setter: self._slider_cb(k, st)))
            self.sliders[key] = s
            z -= 0.105
        self._toggle(self.left, "wireframe", "WIREFRAME", z, app.toggle_wireframe); z -= 0.075
        self._toggle(self.left, "particles", "PARTICLE EFFECTS", z, app.toggle_particles); z -= 0.075
        self._toggle(self.left, "scanning", "SCANNING MODE", z, app.toggle_scanning); z -= 0.075
        self._toggle(self.left, "xray", "X-RAY MODE", z, app.toggle_xray); z -= 0.075
        self._toggle(self.left, "explode", "DISASSEMBLE", z, app.toggle_explode)

        # ------------------------------------------------ more controls (below)
        self.left2 = _panel(TL, 0.03, -1.08, PANEL_W, 0.42, "INSPECTION")
        self._toggle(self.left2, "inspect", "360 INSPECTION", -0.13, app.toggle_inspect)
        self._toggle(self.left2, "paused", "PAUSE ROTATION", -0.205, app.toggle_pause)
        b = DirectButton(parent=self.left2, text="RESET VIEW", text_scale=0.03, text_fg=CY, text_pos=(0, -0.01),
                         frameSize=(-0.31, 0.31, -0.035, 0.035), pos=(PANEL_W / 2, 0, -0.30), relief=DGG.FLAT,
                         frameColor=BTN_OFF, command=app.reset_view, pressEffect=0)

        # ------------------------------------------------ smartwatch information
        self.right = _panel(TR, -PANEL_W - 0.03, -0.03, PANEL_W, 0.80, "SMARTWATCH INFORMATION")
        self.info = {}
        rows = ["DEVICE", "BATTERY", "HEART RATE", "SpO2", "STEPS", "PROJECTION STATUS"]
        z = -0.13
        for r in rows:
            OnscreenText(text=r, parent=self.right, pos=(0.03, z), scale=0.027, fg=DIMC, align=TextNode.ALeft)
            self.info[r] = OnscreenText(text="", parent=self.right, pos=(PANEL_W - 0.03, z), scale=0.034, fg=CY,
                                        align=TextNode.ARight, mayChange=True)
            z -= 0.082
        OnscreenText(text="* ALL HEALTH VALUES ARE DEMO DATA", parent=self.right, pos=(0.03, z - 0.01), scale=0.022,
                     fg=AMB, align=TextNode.ALeft)

        self.logp = _panel(TR, -PANEL_W - 0.03, -0.86, PANEL_W, 0.56, "SYSTEM LOG")
        self.log_lines = [OnscreenText(text="", parent=self.logp, pos=(0.03, -0.125 - i * 0.07), scale=0.026,
                                       fg=(0.5, 0.9, 1.0, 1), align=TextNode.ALeft, mayChange=True) for i in range(6)]
        self.log = []

        # ------------------------------------------------ watch screen selector (bottom)
        self.bottom = DirectFrame(parent=BC, frameSize=(-0.62, 0.62, -0.05, 0.05), pos=(0, 0, 0.14),
                                  frameColor=(0.0, 0.05, 0.1, 0.55), relief=DGG.FLAT)
        self.page_btns = []
        for i, name in enumerate(("HOME", "HEALTH", "FITNESS", "ALERTS", "SOS")):
            btn = DirectButton(parent=self.bottom, text=name, text_scale=0.028, text_fg=RED if name == "SOS" else CY,
                               text_pos=(0, -0.01), frameSize=(-0.11, 0.11, -0.035, 0.035),
                               pos=(-0.48 + i * 0.24, 0, 0), relief=DGG.FLAT, frameColor=BTN_OFF, pressEffect=0,
                               command=app.screen_page, extraArgs=[i])
            self.page_btns.append(btn)
        self.hint = OnscreenText(
            text="DRAG: ROTATE   WHEEL: ZOOM   CLICK WATCH SCREEN: INTERACT   SPACE: PAUSE   1-5: SCREENS   "
                 "X: X-RAY   E: DISASSEMBLE   I: INSPECT   R: RESET   ENTER: SKIP INTRO",
            parent=BC, pos=(0, 0.04), scale=0.024, fg=(0.3, 0.6, 0.7, 1))
        self.msg = OnscreenText(text="", parent=app.aspect2d, pos=(0, -0.62), scale=0.058, fg=CY,
                                shadow=(0, 0, 0, 0.9), mayChange=True)
        self.msg.setTransparency(TransparencyAttrib.MAlpha)
        self.fps_text = OnscreenText(text="", parent=app.a2dBottomRight, pos=(-0.03, 0.03), scale=0.025,
                                     fg=DIMC, align=TextNode.ARight, mayChange=True)
        self.groups = [self.left, self.left2, self.right, self.logp, self.bottom, self.hint, self.status]
        self.sync()

    # --------------------------------------------------------------- widgets
    def _toggle(self, parent, key, label, z, command):
        w = PANEL_W - 0.06
        btn = DirectButton(parent=parent, text=label, text_scale=0.029, text_fg=CY, text_align=TextNode.ALeft,
                           text_pos=(-w / 2 + 0.02, -0.01), frameSize=(-w / 2, w / 2, -0.035, 0.035),
                           pos=(PANEL_W / 2, 0, z), relief=DGG.FLAT, frameColor=BTN_OFF, pressEffect=0,
                           command=lambda k=key, c=command: (c(), self.sync()))
        st = OnscreenText(text="OFF", parent=btn, pos=(w / 2 - 0.02, -0.01), scale=0.029, fg=DIMC,
                          align=TextNode.ARight, mayChange=True)
        self.toggles[key] = (btn, st)

    def _slider_cb(self, key, setter):
        sl = self.sliders.get(key)
        if sl is not None:
            setter(sl["value"])

    def sync(self):
        s = self.app.state
        for key, (btn, st) in self.toggles.items():
            on = bool(getattr(s, key))
            if key == "paused":
                txt = "PAUSED" if on else "ROTATING"
            else:
                txt = "ON" if on else "OFF"
            st.setText(txt)
            st.setFg(GRN if (on and key != "paused") else (AMB if on else DIMC))
            btn["frameColor"] = BTN_ON if on else BTN_OFF
        for key, sl in self.sliders.items():
            if abs(sl["value"] - getattr(s, key)) > 1e-4:
                sl["value"] = getattr(s, key)
        for i, b in enumerate(self.page_btns):
            b["frameColor"] = BTN_ON if i == self.app.screen.page else BTN_OFF

    def log_event(self, text):
        self.log.append(f"[{time.strftime('%H:%M:%S')}] {text}")
        self.log = self.log[-6:]
        for i, line in enumerate(self.log_lines):
            line.setText(self.log[i] if i < len(self.log) else "")

    def set_alpha(self, a):
        for g in self.groups:
            g.setAlphaScale(a)
            if a < 0.01:
                g.hide()
            else:
                g.show()

    def update(self, t, tel, state, fps, caption="", message="", msg_alpha=0.0):
        blink = 0.55 + 0.45 * (1 if int(t * 2) % 2 == 0 else 0.3)
        online = state.projection
        self.status.setText("HOLOGRAM SYSTEM: ONLINE" if online else "HOLOGRAM SYSTEM: STANDBY")
        self.status.setFg((0.0, 0.92 * blink + 0.08, 1.0, 1.0) if online else AMB)
        self.caption.setText(caption)
        self.info["DEVICE"].setText("SmartWatch X")
        self.info["BATTERY"].setText(f"{tel.battery_i}%")
        self.info["HEART RATE"].setText(f"{tel.bpm} BPM")
        self.info["SpO2"].setText(f"{tel.spo2_i}%")
        self.info["STEPS"].setText(f"{tel.steps_i:,}")
        self.info["PROJECTION STATUS"].setText("ACTIVE" if online else "OFFLINE")
        self.info["PROJECTION STATUS"].setFg(GRN if online else RED)
        self.msg.setText(message)
        self.msg.setFg((0.0, 0.92, 1.0, msg_alpha))
        self.fps_text.setText(f"{fps:.0f} FPS")
