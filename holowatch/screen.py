"""Smartwatch display renderer.

Draws the 5 watch screens with Pillow at 2x supersampling and returns an RGBA
image that is uploaded to the 3D screen quad as a texture every frame.  It also
owns the screen's interaction state (current page, SOS state machine, unread
notifications) and a hit-region table so mouse taps on the 3D screen can be
mapped to buttons.
"""
from __future__ import annotations
import math
import os
from PIL import Image, ImageDraw, ImageFont

from .telemetry import Telemetry

W, H = 288, 352
S = 2
PAGES = ["HOME", "HEALTH", "FITNESS", "ALERTS", "SOS"]

CY, BL, WH = (0, 230, 255), (30, 120, 255), (225, 250, 255)
DIM, RED, GRN, AMB = (60, 120, 150), (255, 50, 70), (60, 255, 160), (255, 190, 60)
BG = (2, 9, 16)
TILE = (6, 28, 44)

_FONT_FILES = ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "Helvetica.ttc",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arialbd.ttf"]
_fonts = {}


def font(size):
    size = int(size * S)
    if size not in _fonts:
        f = None
        for name in _FONT_FILES:
            try:
                f = ImageFont.truetype(name, size)
                break
            except OSError:
                continue
        if f is None:
            try:
                f = ImageFont.load_default(size)
            except TypeError:
                f = ImageFont.load_default()
        _fonts[size] = f
    return _fonts[size]


def dim(c, k):
    return tuple(int(v * k) for v in c)


def heart_pts(cx, cy, size):
    pts = []
    for i in range(48):
        t = i / 48 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(((cx + x * size / 34) * S, (cy - y * size / 34) * S))
    return pts


class WatchScreen:
    def __init__(self):
        self.page = 0
        self.page_t = 0.0
        self.t = 0.0
        self.selected = 0.0       # glow 0..1 (set by app when tapped)
        self.sos_state = "idle"   # idle | counting | active
        self.sos_t = 0.0
        self.hits = []
        self.notifs = [
            {"kind": "msg", "title": "Aarav", "body": "Demo day at 4 PM?", "ago": "now", "read": False},
            {"kind": "call", "title": "Missed call", "body": "Mom  -  2 min ago", "ago": "2m", "read": False},
            {"kind": "bell", "title": "Reminder", "body": "Drink water", "ago": "10m", "read": False},
            {"kind": "msg", "title": "Team", "body": "Slides uploaded", "ago": "1h", "read": True},
            {"kind": "bell", "title": "Stand up", "body": "Move for 1 minute", "ago": "2h", "read": True},
        ]
        self._next_notif = 18.0
        self.on_event = None      # callback(str) for log / sound

    # ----------------------------------------------------------- control
    def set_page(self, i):
        i %= len(PAGES)
        if i != self.page:
            self.page, self.page_t = i, 0.0
            if self.on_event:
                self.on_event(f"SCREEN: {PAGES[i]}")

    def next_page(self): self.set_page(self.page + 1)
    def prev_page(self): self.set_page(self.page - 1)

    def unread(self): return sum(1 for n in self.notifs if not n["read"])

    def trigger_sos(self):
        if self.sos_state == "idle":
            self.sos_state, self.sos_t = "counting", 0.0
            self._ev("SOS COUNTDOWN STARTED (DEMO)")
        else:
            self.sos_state = "idle"
            self._ev("SOS CANCELLED")

    def _ev(self, s):
        if self.on_event:
            self.on_event(s)

    def tap(self, px, py):
        """Tap in texture pixel coords. Returns True if a button handled it."""
        for name, (x0, y0, x1, y1) in reversed(self.hits):
            if x0 <= px <= x1 and y0 <= py <= y1:
                if name.startswith("nav"):
                    self.set_page(int(name[3:]))
                elif name.startswith("goto"):
                    self.set_page(int(name[4:]))
                elif name == "sos":
                    self.trigger_sos()
                elif name.startswith("notif"):
                    i = int(name[5:])
                    self.notifs[i]["read"] = not self.notifs[i]["read"]
                    self._ev("NOTIFICATION " + ("READ" if self.notifs[i]["read"] else "UNREAD"))
                return True
        return False

    def update(self, dt):
        self.t += dt
        self.page_t += dt
        if self.sos_state != "idle":
            self.sos_t += dt
            if self.sos_state == "counting" and self.sos_t >= 3.0:
                self.sos_state, self.sos_t = "active", 0.0
                self._ev("EMERGENCY ALERT ACTIVE (SIMULATED)")
        self._next_notif -= dt
        if self._next_notif <= 0:
            self._next_notif = 20.0
            n = self.notifs.pop()
            n.update(read=False, ago="now")
            self.notifs.insert(0, n)
            self.page_t_notif = 0.0

    # ------------------------------------------------------------ render
    def render(self, tel: Telemetry, power=1.0) -> Image.Image:
        img = Image.new("RGBA", (W * S, H * S), BG + (235,))
        d = ImageDraw.Draw(img)
        self.hits = []
        if power > 0.02:
            getattr(self, "_page_" + PAGES[self.page].lower())(d, tel)
            self._chrome(d, tel)
        # rounded-corner mask
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, W * S - 1, H * S - 1), radius=44 * S // 2 * 2, fill=255)
        if self.selected > 0.01:
            d.rounded_rectangle((2, 2, W * S - 3, H * S - 3), radius=44 * S, outline=CY, width=int(2 + 3 * self.selected) * S // 2)
        if power < 0.999:
            y = int(power * H * S)
            d.rectangle((0, y, W * S, H * S), fill=(0, 0, 0, 0))
            if power > 0.0:
                d.rectangle((0, y - 3 * S, W * S, y), fill=CY + (255,))
        a = img.getchannel("A")
        img.putalpha(Image.composite(a, Image.new("L", img.size, 0), mask))
        return img.reduce(S)

    # ------------------------------------------------------------ helpers
    def _t(self, d, xy, s, size=12, fill=WH, anchor="la"):
        d.text((xy[0] * S, xy[1] * S), s, font=font(size), fill=fill, anchor=anchor)

    def _tile(self, d, rect, name=None, outline=DIM):
        x0, y0, x1, y1 = rect
        d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), radius=10 * S, fill=TILE, outline=dim(outline, 0.7), width=S)
        if name:
            self.hits.append((name, rect))

    def _heart(self, d, cx, cy, size, fill=RED):
        d.polygon(heart_pts(cx, cy, size), fill=fill)

    def _arc(self, d, cx, cy, r, w, frac, col):
        box = ((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S)
        d.arc(box, 0, 360, fill=dim(col, 0.22), width=w * S)
        if frac > 0.003:
            d.arc(box, -90, -90 + 360 * min(frac, 1.0), fill=col, width=w * S)

    def _chrome(self, d, tel):
        self._t(d, (28, 7), PAGES[self.page] + "  |  DEMO", 9, DIM)
        # battery
        b = tel.battery_i
        d.rounded_rectangle((206 * S, 8 * S, 232 * S, 18 * S), radius=2 * S, outline=CY, width=S)
        d.rectangle((232 * S, 11 * S, 234 * S, 15 * S), fill=CY)
        d.rectangle((208 * S, 10 * S, (208 + 22 * b / 100) * S, 16 * S), fill=GRN if b > 20 else RED)
        self._t(d, (260, 7), f"{b}%", 9, WH, "ra")
        # nav dots
        for i in range(len(PAGES)):
            cx = 144 + (i - 2) * 26
            on = i == self.page
            d.rounded_rectangle(((cx - (9 if on else 4)) * S, 334 * S, (cx + (9 if on else 4)) * S, 340 * S),
                                radius=3 * S, fill=CY if on else dim(DIM, 0.9))
            self.hits.append((f"nav{i}", (cx - 13, 322, cx + 13, 348)))

    # -------------------------------------------------------------- pages
    def _page_home(self, d, tel):
        hhmm, ss, date = tel.clock()
        self._t(d, (144, 34), date, 12, CY, "ma")
        self._t(d, (144, 52), hhmm, 62, WH, "ma")
        self._t(d, (144, 118), f":{ss}", 16, AMB, "ma")
        # weather
        cx, cy = 52, 148
        d.ellipse(((cx - 8) * S, (cy - 8) * S, (cx + 8) * S, (cy + 8) * S), fill=AMB)
        for k in range(8):
            a = k * math.pi / 4 + self.t * 0.4
            d.line(((cx + 11 * math.cos(a)) * S, (cy + 11 * math.sin(a)) * S,
                    (cx + 15 * math.cos(a)) * S, (cy + 15 * math.sin(a)) * S), fill=AMB, width=2 * S)
        d.ellipse((cx * S, (cy + 2) * S, (cx + 22) * S, (cy + 16) * S), fill=(170, 210, 230))
        self._t(d, (84, 134), "28\u00b0C", 20, WH)
        self._t(d, (84, 160), "PARTLY CLOUDY", 9, DIM)
        # tiles
        pulse = 1 + 0.2 * tel.beat
        self._tile(d, (12, 182, 140, 246), "goto1")
        self._heart(d, 34, 205, 22 * pulse)
        self._t(d, (54, 192), str(tel.bpm), 22, WH)
        self._t(d, (54, 218), "BPM", 9, RED)
        self._t(d, (24, 232), "HEART RATE", 8, DIM)
        self._tile(d, (148, 182, 276, 246), "goto2")
        self._t(d, (160, 190), f"{tel.steps_i:,}", 21, WH)
        self._t(d, (160, 218), "STEPS", 9, GRN)
        self._arc(d, 256, 214, 12, 4, tel.steps / 10000, GRN)
        self._tile(d, (12, 254, 140, 316), "")
        self._arc(d, 40, 285, 15, 5, tel.battery / 100, GRN)
        self._t(d, (62, 270), f"{tel.battery_i}%", 20, WH)
        self._t(d, (62, 297), "BATTERY", 9, DIM)
        self._tile(d, (148, 254, 276, 316), "goto3", AMB if self.unread() else DIM)
        self._t(d, (160, 262), str(self.unread()), 26, AMB if self.unread() else DIM)
        self._t(d, (160, 296), "NEW ALERTS", 9, DIM)

    def _page_health(self, d, tel):
        self._t(d, (16, 30), "HEART RATE", 10, DIM)
        self._t(d, (16, 44), str(tel.bpm), 52, WH)
        self._t(d, (104, 84), "BPM", 12, RED)
        s = 1 + 0.22 * tel.beat
        self._heart(d, 236, 62, 52 * s)
        # ECG strip
        x0, y0, x1, y1 = 12, 118, 276, 188
        d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), radius=8 * S, fill=(3, 18, 28), outline=dim(CY, 0.4), width=S)
        for gx in range(x0 + 22, x1, 22):
            d.line((gx * S, (y0 + 2) * S, gx * S, (y1 - 2) * S), fill=(8, 40, 56), width=1)
        for gy in range(y0 + 14, y1, 14):
            d.line(((x0 + 2) * S, gy * S, (x1 - 2) * S, gy * S), fill=(8, 40, 56), width=1)
        e = tel.ecg[-132:]
        pts = [((x0 + 4 + i * (x1 - x0 - 8) / (len(e) - 1)) * S, (y0 + 48 - float(v) * 34) * S) for i, v in enumerate(e)]
        d.line(pts, fill=dim(GRN, 0.35), width=5 * S // 2)
        d.line(pts, fill=GRN, width=S + 1)
        # stat tiles
        for i, (lab, val, col) in enumerate([("SpO2", f"{tel.spo2_i}%", CY), ("TEMP", f"{tel.temp:.1f}\u00b0C", AMB),
                                           ("SLEEP", f"{tel.sleep_min // 60}h{tel.sleep_min % 60:02d}", BL)]):
            x = 12 + i * 90
            self._tile(d, (x, 198, x + 84, 250))
            self._t(d, (x + 42, 206), lab, 9, col, "ma")
            self._t(d, (x + 42, 222), val, 16, WH, "ma")
        # sleep bars + activity
        self._t(d, (14, 258), "SLEEP MONITOR", 8, DIM)
        stages = [0.3, 0.7, 0.5, 0.9, 0.8, 0.4, 0.6, 1.0, 0.7, 0.5, 0.8, 0.6, 0.4, 0.7]
        for i, v in enumerate(stages):
            h = 28 * v
            d.rounded_rectangle(((14 + i * 12) * S, (292 - h) * S, (22 + i * 12) * S, 292 * S), radius=2 * S, fill=BL if v < 0.75 else CY)
        self._t(d, (190, 258), "ACTIVITY", 8, DIM)
        d.rounded_rectangle((190 * S, 272 * S, 276 * S, 282 * S), radius=5 * S, fill=(8, 40, 56))
        d.rounded_rectangle((190 * S, 272 * S, (190 + 86 * tel.activity) * S, 282 * S), radius=5 * S, fill=AMB)
        self._t(d, (276, 288), f"{int(tel.activity * 100)}%", 11, WH, "ra")
        self._t(d, (144, 312), "DEMO DATA", 8, dim(DIM, 0.8), "ma")

    def _page_fitness(self, d, tel):
        k = min(1.0, self.page_t / 1.2)
        k = 1 - (1 - k) ** 3
        rings = [(66, 11, tel.steps / 10000, GRN), (52, 11, tel.calories / 500, RED), (38, 11, (tel.workout / 60) / 60, CY)]
        for r, w, f, col in rings:
            self._arc(d, 144, 100, r, w, f * k, col)
        self._t(d, (144, 90), f"{int(tel.steps / 100)}%", 18, WH, "ma")
        self._t(d, (144, 111), "GOAL", 8, DIM, "ma")
        cells = [("STEPS", f"{tel.steps_i:,}", GRN), ("CALORIES", f"{int(tel.calories)} kcal", RED),
                 ("DISTANCE", f"{tel.distance:.2f} km", AMB), ("WORKOUT", tel.workout_str(), CY)]
        for i, (lab, val, col) in enumerate(cells):
            x, y = 12 + (i % 2) * 134, 186 + (i // 2) * 66
            self._tile(d, (x, y, x + 130, y + 60))
            d.ellipse(((x + 10) * S, (y + 11) * S, (x + 17) * S, (y + 18) * S), fill=col)
            self._t(d, (x + 24, y + 7), lab, 9, DIM)
            self._t(d, (x + 65, y + 34), val, 15, WH, "ma")
        self._t(d, (144, 322), "", 8)

    def _page_alerts(self, d, tel):
        self._t(d, (16, 30), "NOTIFICATIONS", 12, CY)
        self._t(d, (272, 30), f"{self.unread()} NEW", 11, AMB, "ra")
        for i, n in enumerate(self.notifs[:3]):
            slide = min(1.0, max(0.0, (self.page_t - 0.12 * i) / 0.35))
            slide = 1 - (1 - slide) ** 3
            x0, y0 = 12 + (1 - slide) * 280, 50 + i * 90
            rect = (x0, y0, x0 + 264, y0 + 82)
            call = n["kind"] == "call"
            col = RED if call else (CY if n["kind"] == "msg" else AMB)
            d.rounded_rectangle([v * S for v in rect], radius=12 * S, fill=TILE if n["read"] else (8, 40, 62),
                                outline=col if not n["read"] else dim(DIM, 0.6), width=S)
            cx, cy = x0 + 30, y0 + 41
            d.ellipse(((cx - 17) * S, (cy - 17) * S, (cx + 17) * S, (cy + 17) * S), fill=dim(col, 0.35), outline=col, width=S)
            if n["kind"] == "msg":
                d.rounded_rectangle(((cx - 9) * S, (cy - 7) * S, (cx + 9) * S, (cy + 5) * S), radius=3 * S, fill=WH)
                d.polygon([((cx - 4) * S, (cy + 5) * S), ((cx - 6) * S, (cy + 10) * S), ((cx + 1) * S, (cy + 5) * S)], fill=WH)
            elif call:
                d.arc(((cx - 9) * S, (cy - 9) * S, (cx + 9) * S, (cy + 9) * S), 200, 340, fill=WH, width=3 * S)
                d.ellipse(((cx - 9) * S, (cy - 2) * S, (cx - 4) * S, (cy + 4) * S), fill=WH)
                d.ellipse(((cx + 4) * S, (cy - 2) * S, (cx + 9) * S, (cy + 4) * S), fill=WH)
            else:
                d.pieslice(((cx - 8) * S, (cy - 9) * S, (cx + 8) * S, (cy + 7) * S), 180, 360, fill=WH)
                d.rectangle(((cx - 8) * S, (cy - 1) * S, (cx + 8) * S, (cy + 6) * S), fill=WH)
                d.ellipse(((cx - 2) * S, (cy + 7) * S, (cx + 2) * S, (cy + 11) * S), fill=WH)
            self._t(d, (x0 + 58, y0 + 16), n["title"], 14, WH)
            self._t(d, (x0 + 58, y0 + 42), n["body"], 10, (150, 200, 220))
            self._t(d, (x0 + 252, y0 + 10), n["ago"], 9, DIM, "ra")
            if not n["read"] and int(self.t * 2) % 2 == 0:
                d.ellipse(((x0 + 246) * S, (y0 + 62) * S, (x0 + 254) * S, (y0 + 70) * S), fill=col)
            self.hits.append((f"notif{i}", rect))
        self._t(d, (144, 316), "TAP A CARD TO MARK READ", 8, dim(DIM, 0.9), "ma")

    def _page_sos(self, d, tel):
        cx, cy = 144, 138
        st = self.sos_state
        status = {"idle": ("STANDBY", GRN), "counting": ("ACTIVATING", AMB), "active": ("ALERT ACTIVE", RED)}[st]
        pulse = 0.5 + 0.5 * math.sin(self.t * (3 if st == "idle" else 9))
        if st == "idle":
            for r in (84, 96):
                d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), outline=dim(RED, 0.25 + 0.2 * pulse), width=S)
            d.ellipse(((cx - 72) * S, (cy - 72) * S, (cx + 72) * S, (cy + 72) * S), fill=(190, 20, 40), outline=(255, 120, 130), width=3 * S)
            self._t(d, (cx, cy), "SOS", 54, WH, "mm")
            self._t(d, (cx, 224), "TAP TO ACTIVATE", 10, DIM, "ma")
        elif st == "counting":
            left = max(0.0, 3.0 - self.sos_t)
            for k in range(3):
                r = 40 + ((self.sos_t * 1.2 + k / 3) % 1.0) * 70
                d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), outline=dim(RED, 1 - (r - 40) / 70), width=2 * S)
            d.ellipse(((cx - 58) * S, (cy - 58) * S, (cx + 58) * S, (cy + 58) * S), fill=(190, 20, 40), outline=(255, 120, 130), width=3 * S)
            self._t(d, (cx, cy), str(int(math.ceil(left))), 64, WH, "mm")
            self._t(d, (cx, 224), "TAP TO CANCEL", 10, AMB, "ma")
        else:
            if int(self.sos_t * 4) % 2 == 0:
                d.rounded_rectangle((4 * S, 4 * S, (W - 4) * S, (H - 4) * S), radius=40 * S, outline=RED, width=5 * S)
            d.ellipse(((cx - 64) * S, (cy - 64) * S, (cx + 64) * S, (cy + 64) * S), fill=(120 + int(110 * pulse), 10, 30), outline=(255, 120, 130), width=3 * S)
            self._t(d, (cx, cy - 12), "SOS", 40, WH, "mm")
            self._t(d, (cx, cy + 24), "SENT", 18, WH, "mm")
            self._t(d, (cx, 218), "CALLING CONTACT...", 10, WH, "ma")
            self._t(d, (cx, 234), "LOCATION SHARED (SIMULATED)", 8, AMB, "ma")
        d.ellipse(((60) * S, 262 * S, 68 * S, 270 * S), fill=status[1])
        self._t(d, (76, 258), "STATUS: " + status[0], 12, status[1])
        self._t(d, (144, 292), "2 EMERGENCY CONTACTS  |  DEMO ONLY", 8, dim(DIM, 0.9), "ma")
        self.hits.append(("sos", (cx - 80, cy - 80, cx + 80, cy + 80)))
        self.hits.append(("sos", (0, 0, W, 300))) if st != "idle" else None
