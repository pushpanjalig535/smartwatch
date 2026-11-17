"""Smartwatch display renderer - Unified Platform Edition.

Draws the 7 watch screens (HOME, HEALTH, FITNESS, PAY, BIO, ALERTS, SOS)
with Pillow at 2x supersampling and returns an RGBA image texture.
Integrates Dora Contactless Payments, Bio-Cell Regeneration, and Neon SOS.
"""
from __future__ import annotations
import math
import os
from PIL import Image, ImageDraw, ImageFont

from .telemetry import Telemetry
from .services import EmergencyService, PaymentEngine, BioCellSimulator

W, H = 288, 352
S = 2
PAGES = ["HOME", "HEALTH", "FITNESS", "PAY", "BIO", "ALERTS", "SOS"]

CY, BL, WH = (0, 230, 255), (30, 120, 255), (225, 250, 255)
DIM, RED, GRN, AMB = (60, 120, 150), (255, 50, 70), (60, 255, 160), (255, 190, 60)
PURPLE = (176, 38, 255)
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

        # Integrated services
        self.emergency = EmergencyService()
        self.payments = PaymentEngine()
        self.bio = BioCellSimulator()

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
            self.emergency.log("SOS button pressed - countdown started (5s to cancel)")
            self._ev("SOS COUNTDOWN STARTED (DEMO)")
        else:
            self.sos_state = "idle"
            self.emergency.log("SOS cancelled by user")
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
                # Payments interaction
                elif name == "pay_start":
                    self.payments.start_payment(25000)
                    self._ev("PAYMENT: ENTER PIN")
                elif name == "pay_qr":
                    self.payments.start_payment(12000)
                    self._ev("QR SCAN PAY: ENTER PIN")
                elif name.startswith("key_"):
                    k = name[4:]
                    if k == "clr":
                        self.payments.backspace_digit()
                    elif k == "esc":
                        self.payments.reset_flow()
                        self._ev("PAYMENT CANCELLED")
                    else:
                        done = self.payments.enter_digit(k)
                        if done:
                            self._ev(f"PAYMENT {self.payments.auth_state}: {self.payments.message}")
                elif name == "pay_reset":
                    self.payments.reset_flow()
                # Bio-Cell interaction
                elif name == "cell_next":
                    self.bio.next_cell_type()
                    curr = self.bio.current
                    self._ev(f"DIFFERENTIATION: {curr['name']}")
                return True
        return False

    def update(self, dt):
        self.t += dt
        self.page_t += dt
        self.bio.update(dt)

        if self.sos_state != "idle":
            self.sos_t += dt
            if self.sos_state == "counting" and self.sos_t >= 4.0:
                self.sos_state, self.sos_t = "active", 0.0
                alert_res = self.emergency.dispatch_alert()
                self._ev(f"EMERGENCY ACTIVE: {alert_res}")

        self._next_notif -= dt
        if self._next_notif <= 0:
            self._next_notif = 20.0
            n = self.notifs.pop()
            n.update(read=False, ago="now")
            self.notifs.insert(0, n)

    # ------------------------------------------------------------ render
    def render(self, tel: Telemetry, power=1.0) -> Image.Image:
        img = Image.new("RGBA", (W * S, H * S), BG + (235,))
        d = ImageDraw.Draw(img)
        self.hits = []
        if power > 0.02:
            page_name = PAGES[self.page].lower()
            method = getattr(self, f"_page_{page_name}", None)
            if method:
                method(d, tel)
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
        return img

    def _t(self, d, pos, text, size, fill=WH, anchor="la"):
        x, y = pos[0] * S, pos[1] * S
        d.text((x, y), text, fill=fill, font=font(size), anchor=anchor)

    def _tile(self, d, rect, hit_name="", border=DIM):
        x0, y0, x1, y1 = rect
        d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), radius=10 * S, fill=TILE, outline=border, width=S)
        if hit_name:
            self.hits.append((hit_name, rect))

    def _heart(self, d, cx, cy, size):
        pts = heart_pts(cx, cy, size)
        d.polygon(pts, fill=RED)

    def _arc(self, d, cx, cy, r, w, frac, col):
        box = ((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S)
        d.arc(box, -90, 270, fill=dim(col, 0.25), width=w * S)
        if frac > 0.001:
            d.arc(box, -90, -90 + 360 * min(frac, 1.0), fill=col, width=w * S)

    def _chrome(self, d, tel):
        self._t(d, (24, 7), PAGES[self.page] + "  |  DEMO", 9, DIM)
        # battery
        b = tel.battery_i
        d.rounded_rectangle((206 * S, 8 * S, 232 * S, 18 * S), radius=2 * S, outline=CY, width=S)
        d.rectangle((232 * S, 11 * S, 234 * S, 15 * S), fill=CY)
        d.rectangle((208 * S, 10 * S, (208 + 22 * b / 100) * S, 16 * S), fill=GRN if b > 20 else RED)
        self._t(d, (260, 7), f"{b}%", 9, WH, "ra")

        # 7 nav dots
        count = len(PAGES)
        for i in range(count):
            cx = 144 + (i - (count - 1) / 2) * 20
            on = i == self.page
            d.rounded_rectangle(((cx - (7 if on else 3)) * S, 334 * S, (cx + (7 if on else 3)) * S, 340 * S),
                                radius=3 * S, fill=CY if on else dim(DIM, 0.9))
            self.hits.append((f"nav{i}", (cx - 10, 322, cx + 10, 348)))

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
        self._t(d, (84, 134), "28°C", 20, WH)
        self._t(d, (84, 160), "PARTLY CLOUDY", 9, DIM)

        # Quick Jump tiles
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

        # Bottom tiles: DORA Pay & Bio Cell
        self._tile(d, (12, 254, 140, 316), "goto3", border=dim(CY, 0.8))
        self._t(d, (22, 264), "DORA PAY", 11, CY)
        self._t(d, (22, 282), self.payments.balance_display, 13, WH)
        self._t(d, (22, 300), "TAP TO PAY", 8, DIM)

        self._tile(d, (148, 254, 276, 316), "goto4", border=dim(PURPLE, 0.8))
        self._t(d, (158, 264), "BIO-CELL", 11, PURPLE)
        curr = self.bio.current
        self._t(d, (158, 282), curr["name"].split()[0], 14, WH)
        self._t(d, (158, 300), f"DIFF: {int(self.bio.progress*100)}%", 8, DIM)

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
        self._tile(d, (12, 196, 96, 256), "")
        self._t(d, (54, 204), f"{tel.spo2_i}%", 20, WH, "ma")
        self._t(d, (54, 236), "SpO2", 9, CY, "ma")
        self._tile(d, (102, 196, 186, 256), "")
        self._t(d, (144, 204), f"{tel.temp:.1f}°", 20, WH, "ma")
        self._t(d, (144, 236), "SKIN TEMP", 9, AMB, "ma")
        self._tile(d, (192, 196, 276, 256), "")
        stress_val = int(25 + 15 * math.sin(self.t * 0.1))
        self._t(d, (234, 204), str(stress_val), 20, WH, "ma")
        self._t(d, (234, 236), "STRESS", 9, RED if stress_val > 50 else GRN, "ma")
        self._tile(d, (12, 264, 276, 318), "")
        self._t(d, (24, 274), "HRV: 64 ms", 13, WH)
        self._t(d, (24, 296), "STATUS: NORMAL SINUS RHYTHM", 10, GRN)

    def _page_fitness(self, d, tel):
        self._t(d, (16, 30), "TODAY'S ACTIVITY", 10, DIM)
        cx, cy = 144, 126
        active_mins = int(tel.workout / 60)
        self._arc(d, cx, cy, 72, 8, tel.steps / 10000, RED)
        self._arc(d, cx, cy, 60, 8, active_mins / 45, GRN)
        self._arc(d, cx, cy, 48, 8, active_mins / 30, CY)
        self._t(d, (cx, cy - 14), f"{tel.steps_i:,}", 26, WH, "mm")
        self._t(d, (cx, cy + 14), "/ 10,000 STEPS", 9, DIM, "mm")
        self._tile(d, (12, 208, 96, 270), "")
        self._t(d, (54, 218), f"{int(tel.calories)}", 20, RED, "ma")
        self._t(d, (54, 248), "KCAL", 9, DIM, "ma")
        self._tile(d, (102, 208, 186, 270), "")
        self._t(d, (144, 218), f"{tel.distance:.2f}", 20, GRN, "ma")
        self._t(d, (144, 248), "KM", 9, DIM, "ma")
        self._tile(d, (192, 208, 276, 270), "")
        self._t(d, (234, 218), str(active_mins), 20, CY, "ma")
        self._t(d, (234, 248), "MINS", 9, DIM, "ma")
        self._tile(d, (12, 278, 276, 318), "")
        self._t(d, (24, 288), "GOAL: 78% COMPLETED", 12, WH)
        self._t(d, (24, 304), "PACE: 5.4 KM/H  |  RECOVERY 18H", 9, DIM)

    # ------------------------------------------------- NEW: PAYMENTS SCREEN
    def _page_pay(self, d, tel):
        p = self.payments
        self._t(d, (16, 28), "DORA SECURE PAY", 10, CY)
        self._t(d, (144, 46), p.balance_display, 28, WH, "ma")
        self._t(d, (144, 76), "WALLET BALANCE (NFC ENABLED)", 8, DIM, "ma")

        if p.auth_state == "IDLE":
            # Quick Pay Options & QR
            self._tile(d, (16, 92, 136, 170), "pay_start", CY)
            self._t(d, (76, 106), "TAP & PAY", 12, CY, "ma")
            self._t(d, (76, 126), "Rs. 250", 18, WH, "ma")
            self._t(d, (76, 150), "PRESS TO PAY", 8, DIM, "ma")

            self._tile(d, (152, 92, 272, 170), "pay_qr", AMB)
            self._t(d, (212, 106), "QR PAYMENT", 12, AMB, "ma")
            self._t(d, (212, 126), "Rs. 120", 18, WH, "ma")
            self._t(d, (212, 150), "GENERATE QR", 8, DIM, "ma")

            # Recent transactions list
            self._t(d, (16, 186), "RECENT TRANSACTIONS", 9, DIM)
            y = 202
            for txn in p.transactions[:2]:
                self._tile(d, (12, y, 276, y + 50), "")
                self._t(d, (24, y + 10), txn["merchant"], 12, WH)
                self._t(d, (24, y + 30), f"{txn['time']}  -  {txn['status']}", 8, GRN if txn['status']=="SUCCESS" else RED)
                self._t(d, (264, y + 16), f"-Rs.{txn['amount_paise']/100:.2f}", 12, RED, "ra")
                y += 56
            self._t(d, (144, 318), "PIN PROTECTED  |  OFFLINE SAFE", 8, dim(DIM, 0.9), "ma")

        elif p.auth_state == "PIN_ENTRY":
            # PIN Pad Interface
            self._t(d, (144, 95), f"AMOUNT: Rs. {p.selected_amount_paise/100:.2f}", 12, AMB, "ma")
            dots = " ".join("●" if i < len(p.entered_pin) else "○" for i in range(4))
            self._t(d, (144, 116), dots, 20, CY, "ma")

            # Numeric keypad
            keys = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["<", "0", "X"]]
            sy = 142
            for r_idx, row in enumerate(keys):
                for c_idx, k in enumerate(row):
                    kx0 = 36 + c_idx * 76
                    ky0 = sy + r_idx * 42
                    k_action = "key_clr" if k == "<" else ("key_esc" if k == "X" else f"key_{k}")
                    border_col = RED if k == "X" else (AMB if k == "<" else DIM)
                    self._tile(d, (kx0, ky0, kx0 + 64, ky0 + 36), k_action, border=border_col)
                    self._t(d, (kx0 + 32, ky0 + 10), k, 14, WH, "ma")
            self._t(d, (144, 318), "DEFAULT PIN: 1234", 8, DIM, "ma")

        else:
            # Result state (APPROVED or DECLINED)
            col = GRN if p.auth_state == "APPROVED" else RED
            d.ellipse(((144 - 36) * S, (120 - 36) * S, (144 + 36) * S, (120 + 36) * S), fill=dim(col, 0.3), outline=col, width=2 * S)
            self._t(d, (144, 110), "✓" if p.auth_state == "APPROVED" else "✗", 32, col, "mm")
            self._t(d, (144, 175), p.auth_state, 18, col, "ma")
            self._t(d, (144, 200), p.message, 12, WH, "ma")

            self._tile(d, (60, 240, 228, 290), "pay_reset", col)
            self._t(d, (144, 256), "DONE / RETURN", 12, WH, "ma")

    # ------------------------------------------------- NEW: BIO-CELL SCREEN
    def _page_bio(self, d, tel):
        curr = self.bio.current
        self._t(d, (16, 28), "STEM CELL LAB", 10, PURPLE)
        self._t(d, (272, 28), "v2.4", 9, DIM, "ra")

        # Central Cellular Visualizer (Pillow canvas rendering)
        cx, cy = 144, 125
        c_rgb = curr["color"]
        cycle = self.bio.cycle_time
        k = 1 + 0.05 * math.sin(cycle * 3.0)
        r = 50 * k

        # Multi-layer glowing cellular membrane
        for layer in range(6, 0, -1):
            lr = r + layer * 4
            d.ellipse(((cx - lr) * S, (cy - lr) * S, (cx + lr) * S, (cy + lr) * S),
                      fill=dim(c_rgb, 0.04 * (7 - layer)))
        d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S),
                  fill=dim(c_rgb, 0.4), outline=c_rgb, width=2 * S)

        # Cell nucleus (mitochondria and core)
        nr = 18 * (1 + 0.08 * math.sin(cycle * 6.0))
        d.ellipse(((cx - nr) * S, (cy - nr) * S, (cx + nr) * S, (cy + nr) * S),
                  fill=dim(c_rgb, 0.8), outline=WH, width=S)
        # Membrane receptors
        for i in range(8):
            ang = i * math.pi / 4 + cycle * 0.5
            dx, dy = math.cos(ang), math.sin(ang)
            bx, by = cx + dx * r, cy + dy * r
            tx, ty = cx + dx * (r + 8), cy + dy * (r + 8)
            d.line((bx * S, by * S, tx * S, ty * S), fill=CY, width=2 * S)

        # Cell label and status
        self._t(d, (cx, 185), curr["name"].upper(), 16, WH, "ma")
        self._t(d, (cx, 206), f"TARGET: {curr['target']}", 9, CY, "ma")

        # Differentiation progress & pathway
        self._tile(d, (12, 224, 276, 276), "cell_next", border=dim(c_rgb, 0.7))
        self._t(d, (24, 234), f"SIGNAL: {curr['signal']}", 10, WH)
        self._t(d, (24, 252), "STATUS: REGENERATING...", 9, GRN)
        self._t(d, (264, 244), "TAP >>", 10, AMB, "ra")

        # Progress bar
        prog = self.bio.progress
        d.rounded_rectangle((12 * S, 286 * S, 276 * S, 296 * S), radius=4 * S, fill=(10, 30, 45))
        d.rounded_rectangle((12 * S, 286 * S, int(12 + 264 * prog) * S, 296 * S), radius=4 * S, fill=c_rgb)
        self._t(d, (144, 306), f"DIFFERENTIATION PROGRESS: {int(prog*100)}%", 8, DIM, "ma")

    def _page_alerts(self, d, tel):
        self._t(d, (16, 30), "NOTIFICATIONS", 10, DIM)
        self._t(d, (272, 30), f"{self.unread()} NEW", 10, AMB if self.unread() else DIM, "ra")
        for i, n in enumerate(self.notifs[:4]):
            y0 = 50 + i * 65
            rect = (12, y0, 276, y0 + 58)
            col = AMB if not n["read"] else DIM
            call = n["kind"] == "call"
            if call and not n["read"]:
                col = RED
            self._tile(d, rect, "", col)
            cx, cy = 38, y0 + 29
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
            self._t(d, (x0 := rect[0] + 58, y0 + 16), n["title"], 14, WH)
            self._t(d, (x0, y0 + 40), n["body"], 10, (150, 200, 220))
            self._t(d, (rect[2] - 18, y0 + 10), n["ago"], 9, DIM, "ra")
            if not n["read"] and int(self.t * 2) % 2 == 0:
                d.ellipse(((rect[2] - 22) * S, (y0 + 42) * S, (rect[2] - 14) * S, (y0 + 50) * S), fill=col)
            self.hits.append((f"notif{i}", rect))
        self._t(d, (144, 316), "TAP A CARD TO MARK READ", 8, dim(DIM, 0.9), "ma")

    # ------------------------------------------------- ENHANCED: NEON SOS SCREEN
    def _page_sos(self, d, tel):
        cx, cy = 144, 134
        st = self.sos_state
        status = {"idle": ("STANDBY", GRN), "counting": ("ACTIVATING", AMB), "active": ("ALERT ACTIVE", RED)}[st]
        pulse = 0.5 + 0.5 * math.sin(self.t * (3 if st == "idle" else 9))

        if st == "idle":
            for r in (84, 96):
                d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), outline=dim(RED, 0.25 + 0.2 * pulse), width=S)
            d.ellipse(((cx - 72) * S, (cy - 72) * S, (cx + 72) * S, (cy + 72) * S), fill=(190, 20, 40), outline=(255, 120, 130), width=3 * S)
            self._t(d, (cx, cy), "SOS", 54, WH, "mm")
            self._t(d, (cx, 218), "TAP TO ACTIVATE", 10, DIM, "ma")
        elif st == "counting":
            left = max(0.0, 4.0 - self.sos_t)
            for k in range(3):
                r = 40 + ((self.sos_t * 1.2 + k / 3) % 1.0) * 70
                d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), outline=dim(RED, 1 - (r - 40) / 70), width=2 * S)
            d.ellipse(((cx - 58) * S, (cy - 58) * S, (cx + 58) * S, (cy + 58) * S), fill=(190, 20, 40), outline=(255, 120, 130), width=3 * S)
            self._t(d, (cx, cy), str(int(math.ceil(left))), 64, WH, "mm")
            self._t(d, (cx, 218), "TAP TO CANCEL", 10, AMB, "ma")
        else:
            if int(self.sos_t * 4) % 2 == 0:
                d.rounded_rectangle((4 * S, 4 * S, (W - 4) * S, (H - 4) * S), radius=40 * S, outline=RED, width=5 * S)
            d.ellipse(((cx - 64) * S, (cy - 64) * S, (cx + 64) * S, (cy + 64) * S), fill=(120 + int(110 * pulse), 10, 30), outline=(255, 120, 130), width=3 * S)
            self._t(d, (cx, cy - 12), "SOS", 40, WH, "mm")
            self._t(d, (cx, cy + 24), "SENT", 18, WH, "mm")
            self._t(d, (cx, 214), f"BEACON: {self.emergency.lat:.4f}N, {self.emergency.lon:.4f}E", 9, AMB, "ma")
            self._t(d, (cx, 230), f"DISPATCHED TO {len(self.emergency.contacts)} CONTACTS", 9, WH, "ma")

        d.ellipse(((48) * S, 258 * S, 56 * S, 266 * S), fill=status[1])
        self._t(d, (64, 254), "STATUS: " + status[0], 11, status[1])
        self._t(d, (144, 284), f"GPS ACTIVE  |  {len(self.emergency.contacts)} CONTACTS LOADED", 8, dim(DIM, 0.9), "ma")
        self._t(d, (144, 300), "WRITES TO sos_outbox.txt & sos_log.txt", 8, DIM, "ma")

        self.hits.append(("sos", (cx - 80, cy - 80, cx + 80, cy + 80)))
        if st != "idle":
            self.hits.append(("sos", (0, 0, W, 300)))
