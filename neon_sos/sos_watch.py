# =====================================================================
#  HOLOGRAM SOS - NEON SMARTWATCH SIMULATION
#
#  Module of the project:
#  "A Context-Aware Self-Transforming Smartwatch Interface for
#   Emergency Response and Secure Payments"
#
#  SIMULATION ONLY: no real GPS, calls, SMS or internet are used.
#  Run with:   py sos_watch.py
# =====================================================================

import tkinter as tk
import datetime
import time
import math
import random
import os

# ---------------------------------------------------------------------
# SETTINGS - change these numbers to change how the watch behaves
# ---------------------------------------------------------------------
HOLD_SECONDS = 1             # SOS button must be held this long
COUNTDOWN_SECONDS = 5        # time the user has to cancel
TRIGGER_FLASH_SECONDS = 0.5  # short "SOS TRIGGERED" flash before countdown
CANCEL_MESSAGE_SECONDS = 2   # "SOS CANCELLED" shows this long, then normal
TICK_MS = 40                 # screen refresh interval (milliseconds)

# Sample coordinates - NOT taken from any real GPS hardware
BASE_LATITUDE = 12.9716
BASE_LONGITUDE = 77.5946

# All files are kept in the same folder as this program
FOLDER = os.path.dirname(os.path.abspath(__file__))
CONTACTS_FILE = os.path.join(FOLDER, "contacts.txt")
LOG_FILE = os.path.join(FOLDER, "sos_log.txt")
OUTBOX_FILE = os.path.join(FOLDER, "sos_outbox.txt")

# ---------------------------------------------------------------------
# NEON COLOURS
# ---------------------------------------------------------------------
BG = "#05070f"          # very dark navy background
PANEL = "#0b1226"       # slightly lighter panels
CYAN = "#00f0ff"        # primary neon
BLUE = "#2f7bff"        # secondary electric blue
PURPLE = "#b026ff"      # accent neon purple
RED = "#ff2a4d"         # emergency red
AMBER = "#ffb020"       # warning (countdown)
WHITE = "#e8f4ff"       # main text
GREY = "#7d8ba5"        # secondary text
DARK_GREY = "#26304a"

# Colour steps used for the "breathing" glow animation
CYAN_PULSE = ["#00434d", "#006673", "#008c99", "#00b3c2", "#008c99", "#006673"]
RED_PULSE = ["#ff2a4d", "#e5203f", "#c01632", "#a00f28", "#c01632", "#e5203f"]

# Fonts. A NEGATIVE size means "size in pixels", so the text always fits
# inside the drawn watch, whatever the Windows display scaling is.
MONO = "Consolas"
UI = "Segoe UI"

# Watch geometry (all in pixels on the canvas)
CANVAS_W = 380
CANVAS_H = 620
CX = 190            # horizontal centre of the watch
SOS_Y = 310         # vertical centre of the SOS button
SOS_RADIUS = 64     # size of the SOS button

# ---------------------------------------------------------------------
# PROGRAM DATA (variables that change while the program runs)
# ---------------------------------------------------------------------
state = "NORMAL"        # NORMAL, TRIGGERED, COUNTDOWN, ACTIVE, CANCELLED
holding = False         # True while the SOS button is being held
hold_start_time = 0.0   # when the user started holding
phase_end_time = 0.0    # when the current timed phase should finish
activation_time = ""    # clock time when SOS became active
active_since = 0.0      # used to show "active for mm:ss"
latitude = BASE_LATITUDE
longitude = BASE_LONGITUDE
battery_level = 87      # simulated battery %
network_bars = 3        # simulated signal strength (0 to 4)
last_battery_change = time.time()
last_network_change = time.time()
tick_count = 0          # counts screen refreshes (used for animation)
contacts = []


# =====================================================================
# SMALL HELPER FUNCTIONS
# =====================================================================
def now_text():
    return datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def write_to_file(path, text):
    # Saving files should never crash the watch, so errors are ignored
    try:
        with open(path, "a", encoding="utf-8") as file:
            file.write(text)
    except OSError:
        pass


def load_contacts():
    # Reads contacts.txt. Each line:  Name, phone, relation (relation optional)
    loaded = []
    try:
        with open(CONTACTS_FILE, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line == "" or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    relation = "Emergency contact"
                    if len(parts) >= 3:
                        relation = parts[2].strip()
                    loaded.append({"name": parts[0].strip(),
                                   "phone": parts[1].strip(),
                                   "relation": relation})
    except OSError:
        pass

    # If the file is missing or empty, use sample contacts so the demo works
    if len(loaded) == 0:
        loaded = [
            {"name": "Contact One", "phone": "+910000000001", "relation": "Parent"},
            {"name": "Contact Two", "phone": "+910000000002", "relation": "Friend"},
            {"name": "Campus Security", "phone": "+910000000003", "relation": "Security"},
        ]
    return loaded


def lat_text():
    return f"LAT  {latitude:.5f} N"


def lon_text():
    return f"LON  {longitude:.5f} E"


def log_event(message):
    # Adds one line to the on-screen event log AND to sos_log.txt
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_box.config(state="normal")
    log_box.insert("end", stamp + "  ", "time")
    log_box.insert("end", message + "\n")
    log_box.see("end")
    log_box.config(state="disabled")
    write_to_file(LOG_FILE, now_text() + " - " + message + "\n")


# =====================================================================
# DRAWING HELPERS (the watch is drawn on a Tkinter Canvas)
# =====================================================================
def rounded_rect(x1, y1, x2, y2, radius, fill, outline, width, tags):
    # Tkinter has no rounded rectangle, so we draw a smoothed polygon
    points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
              x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
              x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, fill=fill,
                                 outline=outline, width=width, tags=tags)


def clear_screen():
    # Removes everything drawn on the watch display (not the watch body)
    canvas.delete("screen")
    canvas.config(cursor="")


def draw_watch_body():
    # Straps with simple texture lines (drawn with a loop)
    rounded_rect(118, 0, 262, 80, 14, "#0a0f1e", "#141c33", 1, "body")
    rounded_rect(118, 540, 262, 620, 14, "#0a0f1e", "#141c33", 1, "body")
    for y in range(12, 70, 12):
        canvas.create_line(132, y, 248, y, fill="#121b33", tags="body")
        canvas.create_line(132, 620 - y, 248, 620 - y, fill="#121b33", tags="body")

    # Watch case
    rounded_rect(40, 50, 340, 570, 64, "#080c1a", "", 1, "body")

    # Neon glow border: several outlines, darkest on the outside
    glow_colours = ["#002229", "#004652", "#00808f", CYAN]
    for i in range(4):
        grow = (3 - i) * 3
        rounded_rect(40 - grow, 50 - grow, 340 + grow, 570 + grow, 64 + grow,
                     "", glow_colours[i], 2, "body")

    # Side buttons (crown)
    rounded_rect(339, 236, 353, 296, 5, BLUE, BLUE, 1, "body")
    rounded_rect(339, 320, 351, 352, 4, PURPLE, PURPLE, 1, "body")

    # Display glass
    rounded_rect(58, 78, 322, 542, 46, "#03050c", "#123049", 1, "body")


def draw_button(x1, y1, x2, y2, text, fill, text_colour, outline, glow, tag):
    # A rounded neon button drawn on the canvas. All parts share one tag,
    # so clicking anywhere on it calls the same function.
    rounded_rect(x1 - 5, y1 - 5, x2 + 5, y2 + 5, 28, "", glow, 2, ("screen", tag))
    rounded_rect(x1, y1, x2, y2, 24, fill, outline, 2, ("screen", tag))
    canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, fill=text_colour,
                       font=(MONO, -22, "bold"), tags=("screen", tag))


# =====================================================================
# THE FOUR WATCH SCREENS
# =====================================================================
def draw_normal_screen():
    clear_screen()

    # --- status bar: simulated network (left) and battery (right) ---
    canvas.create_text(92, 104, text="LTE", fill=GREY, anchor="w",
                       font=(MONO, -12, "bold"), tags="screen")
    for i in range(4):
        x = 122 + i * 7
        height = 4 + i * 3
        canvas.create_rectangle(x, 109 - height, x + 4, 109, outline="",
                                fill=DARK_GREY, tags=("screen", "bar" + str(i)))
    canvas.create_text(252, 104, text="", fill=WHITE, anchor="e",
                       font=(MONO, -12, "bold"), tags=("screen", "battery_text"))
    canvas.create_rectangle(256, 98, 280, 110, outline=GREY, tags="screen")
    canvas.create_rectangle(280, 101, 283, 107, fill=GREY, outline="", tags="screen")
    canvas.create_rectangle(258, 100, 258, 109, fill=CYAN, outline="",
                            tags=("screen", "battery_fill"))

    # --- digital clock and date ---
    canvas.create_text(CX, 146, text="", fill=CYAN, font=(MONO, -40, "bold"),
                       tags=("screen", "clock"))
    canvas.create_text(CX, 180, text="", fill=BLUE, font=(MONO, -12, "bold"),
                       tags=("screen", "date"))

    # --- HUD tick marks around the SOS button (drawn with a loop) ---
    for i in range(24):
        angle = math.radians(i * 15)
        inner = 87
        colour = DARK_GREY
        if i % 6 == 0:
            inner = 82
            colour = PURPLE
        x1 = CX + inner * math.cos(angle)
        y1 = SOS_Y + inner * math.sin(angle)
        x2 = CX + 93 * math.cos(angle)
        y2 = SOS_Y + 93 * math.sin(angle)
        canvas.create_line(x1, y1, x2, y2, fill=colour, width=2, tags="screen")

    # --- glowing ring + hold-progress arc ---
    canvas.create_oval(CX - 76, SOS_Y - 76, CX + 76, SOS_Y + 76, width=2,
                       outline=CYAN_PULSE[0], tags=("screen", "pulse_cyan"))
    canvas.create_arc(CX - 76, SOS_Y - 76, CX + 76, SOS_Y + 76, start=90,
                      extent=0, style="arc", outline=CYAN, width=6,
                      tags=("screen", "hold_arc"))

    # --- the SOS button itself ---
    r = SOS_RADIUS
    canvas.create_oval(CX - r, SOS_Y - r, CX + r, SOS_Y + r, fill="#3a0010",
                       outline=RED, width=3, tags=("screen", "sos_button", "sos_core"))
    canvas.create_oval(CX - r + 10, SOS_Y - r + 10, CX + r - 10, SOS_Y + r - 10,
                       outline="#7a0a22", width=1, tags=("screen", "sos_button"))
    canvas.create_text(CX, SOS_Y - 6, text="SOS", fill=WHITE,
                       font=(MONO, -38, "bold"), tags=("screen", "sos_button"))
    canvas.create_text(CX, SOS_Y + 26, text="HOLD " + str(HOLD_SECONDS) + " SEC",
                       fill="#ff9aaa", font=(MONO, -11, "bold"),
                       tags=("screen", "sos_button"))

    # --- hint, emergency contact and ready status ---
    canvas.create_text(CX, 418, text="HOLD TO ACTIVATE SOS", fill=CYAN,
                       font=(MONO, -12, "bold"), tags=("screen", "hint"))
    first = contacts[0]
    canvas.create_text(CX, 448, text="ICE  >  " + first["name"], fill=WHITE,
                       font=(UI, -13, "bold"), tags="screen")
    canvas.create_text(CX, 466, text=first["phone"], fill=GREY,
                       font=(MONO, -11), tags="screen")
    canvas.create_text(CX, 500, text="\u25cf SYSTEM READY", fill=CYAN,
                       font=(MONO, -11, "bold"), tags="screen")

    update_clock()
    update_status_bar()


def draw_countdown_screen():
    clear_screen()
    canvas.create_text(CX, 112, text="SOS TRIGGERED", fill=RED,
                       font=(MONO, -22, "bold"), tags=("screen", "pulse_red"))
    canvas.create_text(CX, 138, text="Preparing countdown...", fill=GREY,
                       font=(MONO, -11), tags=("screen", "count_sub"))

    # Countdown ring: dark track + red arc that shrinks smoothly
    canvas.create_oval(CX - 86, 164, CX + 86, 336, outline="#2a0710", width=1,
                       tags="screen")
    canvas.create_oval(CX - 72, 178, CX + 72, 322, outline="#3a0a16", width=10,
                       tags="screen")
    canvas.create_arc(CX - 72, 178, CX + 72, 322, start=90, extent=-359.9,
                      style="arc", outline=RED, width=10, tags=("screen", "count_arc"))
    canvas.create_text(CX, 244, text=str(COUNTDOWN_SECONDS), fill=WHITE,
                       font=(MONO, -60, "bold"), tags=("screen", "count_text"))
    canvas.create_text(CX, 284, text="SECONDS", fill=GREY,
                       font=(MONO, -10, "bold"), tags="screen")

    canvas.create_text(CX, 354, text="Alert will go to " + str(len(contacts))
                       + " contacts", fill=GREY, font=(MONO, -11), tags="screen")

    # Big, bright CANCEL button
    draw_button(100, 380, 280, 436, "CANCEL", CYAN, BG, CYAN, "#00606b", "cancel_btn")
    canvas.create_text(CX, 472, text="Accidental? Tap CANCEL (or Esc)",
                       fill=GREY, font=(MONO, -10), tags="screen")


def draw_cancelled_screen():
    clear_screen()
    canvas.create_oval(CX - 56, 184, CX + 56, 296, outline=PURPLE, width=4,
                       tags="screen")
    canvas.create_line(CX - 22, 218, CX + 22, 262, fill=PURPLE, width=6, tags="screen")
    canvas.create_line(CX + 22, 218, CX - 22, 262, fill=PURPLE, width=6, tags="screen")
    canvas.create_text(CX, 345, text="SOS CANCELLED", fill=PURPLE,
                       font=(MONO, -22, "bold"), tags="screen")
    canvas.create_text(CX, 375, text="No alert was prepared", fill=WHITE,
                       font=(UI, -13), tags="screen")
    canvas.create_text(CX, 400, text="Returning to watch face...", fill=GREY,
                       font=(MONO, -11), tags="screen")


def draw_active_screen():
    clear_screen()

    # Pulsing red banner
    rounded_rect(72, 92, 308, 164, 22, "", "#5a0718", 2, "screen")
    rounded_rect(76, 96, 304, 160, 20, RED, "", 1, ("screen", "pulse_red"))
    canvas.create_text(CX, 128, text="SOS ACTIVE", fill=WHITE,
                       font=(MONO, -30, "bold"), tags="screen")

    canvas.create_text(CX, 184, text="EMERGENCY MODE ON", fill=RED,
                       font=(MONO, -13, "bold"), tags="screen")
    canvas.create_text(CX, 206, text="Activated at " + activation_time, fill=WHITE,
                       font=(MONO, -11), tags="screen")
    canvas.create_text(CX, 224, text="Active for 00:00", fill=GREY,
                       font=(MONO, -11), tags=("screen", "elapsed"))
    canvas.create_line(96, 242, 284, 242, fill="#123049", tags="screen")

    # Simulated GPS
    canvas.create_text(CX, 258, text="LOCATION  [SIMULATED]", fill=CYAN,
                       font=(MONO, -10, "bold"), tags="screen")
    canvas.create_text(CX, 278, text=lat_text(), fill=WHITE,
                       font=(MONO, -13), tags=("screen", "gps_lat"))
    canvas.create_text(CX, 296, text=lon_text(), fill=WHITE,
                       font=(MONO, -13), tags=("screen", "gps_lon"))

    # Simulated alerts (show at most 4 names so the screen is not crowded)
    canvas.create_text(CX, 322, text="ALERTS  [DEMO MODE]", fill=CYAN,
                       font=(MONO, -10, "bold"), tags="screen")
    y = 342
    for i in range(len(contacts)):
        if i == 4:
            canvas.create_text(CX, y, text="+ " + str(len(contacts) - 4) + " more",
                               fill=GREY, font=(UI, -12), tags="screen")
            break
        canvas.create_text(CX, y, text="\u00bb " + contacts[i]["name"], fill=WHITE,
                           font=(UI, -12), tags="screen")
        y = y + 18
    canvas.create_text(CX, 432, text="Emergency notifications\ngenerated successfully",
                       fill=PURPLE, font=(MONO, -10, "bold"), justify="center",
                       tags="screen")

    draw_button(100, 458, 280, 504, "RESET", "#140a26", PURPLE, PURPLE, "#3d1259",
                "reset_btn")


# =====================================================================
# LIVE UPDATES (clock, battery, network)
# =====================================================================
def update_clock():
    now = datetime.datetime.now()
    canvas.itemconfig("clock", text=now.strftime("%H:%M:%S"))
    canvas.itemconfig("date", text=now.strftime("%a  %d %b %Y").upper())


def update_status_bar():
    canvas.itemconfig("battery_text", text=str(battery_level) + "%")
    colour = CYAN
    if battery_level <= 20:
        colour = RED
    canvas.coords("battery_fill", 258, 100, 258 + 21 * battery_level / 100, 109)
    canvas.itemconfig("battery_fill", fill=colour)
    for i in range(4):
        if i < network_bars:
            canvas.itemconfig("bar" + str(i), fill=CYAN)
        else:
            canvas.itemconfig("bar" + str(i), fill=DARK_GREY)


def update_simulated_sensors(now):
    global battery_level, network_bars, last_battery_change, last_network_change
    # Battery drops 1% every 60 seconds (never below 5%)
    if now - last_battery_change >= 60 and battery_level > 5:
        battery_level = battery_level - 1
        last_battery_change = now
    # Signal strength changes randomly every 8 seconds
    if now - last_network_change >= 8:
        network_bars = random.randint(2, 4)
        last_network_change = now
    update_status_bar()


# =====================================================================
# STATE CHANGES  (NORMAL -> TRIGGERED -> COUNTDOWN -> ACTIVE)
# =====================================================================
def set_state(new_state):
    # Changes the state and lights up the matching box on the dashboard
    global state
    state = new_state
    for name in flow_labels:
        if name == state:
            flow_labels[name].config(bg=STATE_COLOURS[name], fg=BG)
        else:
            flow_labels[name].config(bg=PANEL, fg=GREY)


def trigger_sos():
    global phase_end_time
    set_state("TRIGGERED")
    phase_end_time = time.time() + TRIGGER_FLASH_SECONDS
    draw_countdown_screen()
    log_event("SOS triggered (button held " + str(HOLD_SECONDS) + " s)")


def start_countdown():
    global phase_end_time
    set_state("COUNTDOWN")
    phase_end_time = time.time() + COUNTDOWN_SECONDS
    canvas.itemconfig("count_sub", text="Cancel within " + str(COUNTDOWN_SECONDS)
                      + " seconds")
    log_event("Countdown started - " + str(COUNTDOWN_SECONDS) + " s to cancel")


def cancel_sos():
    global phase_end_time
    if state != "TRIGGERED" and state != "COUNTDOWN":
        return
    set_state("CANCELLED")
    phase_end_time = time.time() + CANCEL_MESSAGE_SECONDS
    draw_cancelled_screen()
    alert_label.config(text="SOS cancelled by user.\nNo alert was prepared.", fg=PURPLE)
    log_event("SOS cancelled by user - no alert prepared")


def return_to_normal():
    set_state("NORMAL")
    draw_normal_screen()
    alert_label.config(text=STANDBY_TEXT, fg=GREY)
    log_event("Returned to normal watch screen")


def activate_sos():
    global activation_time, active_since
    set_state("ACTIVE")
    activation_time = datetime.datetime.now().strftime("%H:%M:%S")
    active_since = time.time()
    draw_active_screen()
    log_event("SOS ACTIVATED - emergency mode on")
    prepare_notifications()


def prepare_notifications():
    # Builds the simulated messages. NOTHING is actually sent.
    panel_text = ""
    file_text = "\n" + now_text() + " - SIMULATED SOS ALERT\n"
    file_text = file_text + "Location (simulated): " + lat_text() + ", " + lon_text() + "\n"
    for contact in contacts:
        message = ("SOS! Emergency assistance needed. Simulated location: "
                   + f"{latitude:.5f}, {longitude:.5f}")
        panel_text = panel_text + "\u00bb " + contact["name"] + "  " + contact["phone"] + "\n"
        panel_text = panel_text + "   [SIMULATED - message prepared]\n"
        file_text = file_text + "To: " + contact["name"] + " (" + contact["phone"] + ")\n"
        file_text = file_text + "Message: " + message + "\n"
        file_text = file_text + "Transmitted: NO - simulation only\n"

    alert_label.config(text=panel_text.strip(), fg=WHITE)
    write_to_file(OUTBOX_FILE, file_text)
    log_event("Simulated messages prepared for " + str(len(contacts)) + " contacts")


def reset_system():
    if state != "ACTIVE":
        return
    set_state("NORMAL")
    draw_normal_screen()
    alert_label.config(text=STANDBY_TEXT, fg=GREY)
    log_event("System reset - back to normal")


def update_location():
    # Moves the sample location slightly to SIMULATE a GPS update
    global latitude, longitude
    latitude = BASE_LATITUDE + random.uniform(-0.002, 0.002)
    longitude = BASE_LONGITUDE + random.uniform(-0.002, 0.002)
    lat_label.config(text=lat_text())
    lon_label.config(text=lon_text())
    gps_time_label.config(text="Updated " + datetime.datetime.now().strftime("%H:%M:%S"))
    canvas.itemconfig("gps_lat", text=lat_text())
    canvas.itemconfig("gps_lon", text=lon_text())
    log_event(f"Simulated GPS updated: {latitude:.5f}, {longitude:.5f}")


# =====================================================================
# MOUSE AND KEYBOARD EVENTS
# =====================================================================
def sos_pressed(event):
    global holding, hold_start_time
    if state != "NORMAL":
        return
    holding = True
    hold_start_time = time.time()
    canvas.itemconfig("sos_core", fill=RED)          # button lights up
    log_event("SOS button pressed - holding...")


def sos_released(event):
    global holding
    if holding:
        # Let go too early: this protects against accidental activation
        holding = False
        canvas.itemconfig("sos_core", fill="#3a0010")
        canvas.itemconfig("hold_arc", extent=0)
        canvas.itemconfig("hint", text="HOLD TO ACTIVATE SOS")
        log_event("Released before " + str(HOLD_SECONDS) + " s - SOS not triggered")


def sos_moved(event):
    # Dragging the pointer off the button also counts as letting go
    distance = math.hypot(event.x - CX, event.y - SOS_Y)
    if holding and distance > SOS_RADIUS:
        sos_released(event)


def cancel_clicked(event):
    cancel_sos()


def reset_clicked(event):
    reset_system()


def escape_pressed(event):
    cancel_sos()


def show_hand(event):
    canvas.config(cursor="hand2")


def show_arrow(event):
    canvas.config(cursor="")


def close_app():
    log_event("Application closed")
    root.destroy()


# =====================================================================
# HEARTBEAT - runs every TICK_MS milliseconds using root.after()
# (no time.sleep(), so the window never freezes)
# =====================================================================
def heartbeat():
    global tick_count, holding
    root.after(TICK_MS, heartbeat)       # schedule the next tick first
    tick_count = tick_count + 1
    now = time.time()

    update_clock()
    update_simulated_sensors(now)

    if state == "NORMAL" and holding:
        progress = (now - hold_start_time) / HOLD_SECONDS
        if progress >= 1:
            holding = False
            trigger_sos()
        else:
            canvas.itemconfig("hold_arc", extent=-359.9 * progress)
            canvas.itemconfig("hint", text="HOLDING...  " + str(int(progress * 100)) + "%")

    elif state == "TRIGGERED":
        if now >= phase_end_time:
            start_countdown()

    elif state == "COUNTDOWN":
        remaining = phase_end_time - now
        if remaining <= 0:
            activate_sos()
        else:
            canvas.itemconfig("count_arc", extent=-359.9 * remaining / COUNTDOWN_SECONDS)
            canvas.itemconfig("count_text", text=str(math.ceil(remaining)))

    elif state == "CANCELLED":
        if now >= phase_end_time:
            return_to_normal()

    elif state == "ACTIVE":
        seconds = int(now - active_since)
        canvas.itemconfig("elapsed", text=f"Active for {seconds // 60:02d}:{seconds % 60:02d}")

    # Glow animation: step through the colour lists
    step = (tick_count // 3) % len(CYAN_PULSE)
    canvas.itemconfig("pulse_cyan", outline=CYAN_PULSE[step])
    canvas.itemconfig("pulse_red", fill=RED_PULSE[step])


# =====================================================================
# BUILD THE WINDOW
# =====================================================================
contacts = load_contacts()

root = tk.Tk()
root.title("Hologram SOS - Neon Smartwatch Simulation")
root.configure(bg=BG)
root.resizable(False, False)

# ---------- LEFT: the smartwatch ----------
canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg=BG, highlightthickness=0)
canvas.grid(row=0, column=0, padx=(16, 8), pady=10)

# Mouse bindings for the canvas buttons (set once, work for every redraw)
canvas.tag_bind("sos_button", "<ButtonPress-1>", sos_pressed)
canvas.tag_bind("sos_button", "<ButtonRelease-1>", sos_released)
canvas.tag_bind("sos_button", "<B1-Motion>", sos_moved)
canvas.tag_bind("cancel_btn", "<Button-1>", cancel_clicked)
canvas.tag_bind("reset_btn", "<Button-1>", reset_clicked)
for clickable in ["sos_button", "cancel_btn", "reset_btn"]:
    canvas.tag_bind(clickable, "<Enter>", show_hand)
    canvas.tag_bind(clickable, "<Leave>", show_arrow)
root.bind("<Escape>", escape_pressed)

# ---------- RIGHT: the holographic dashboard ----------
dash = tk.Frame(root, bg=BG)
dash.grid(row=0, column=1, sticky="n", padx=(8, 20), pady=18)


def section_title(parent, text, colour):
    label = tk.Label(parent, text=text, font=(MONO, -11, "bold"), fg=colour, bg=BG)
    label.pack(anchor="w", pady=(12, 4))


def make_panel(parent, border_colour):
    # A dark panel with a thin neon border
    return tk.Frame(parent, bg=PANEL, highlightthickness=1,
                    highlightbackground=border_colour, highlightcolor=border_colour)


tk.Label(dash, text="HOLOGRAM SOS", font=(MONO, -28, "bold"), fg=CYAN,
         bg=BG).pack(anchor="w")
tk.Label(dash, text="EMERGENCY RESPONSE MODULE  //  SMARTWATCH SIMULATION",
         font=(MONO, -11), fg=GREY, bg=BG).pack(anchor="w")

# State flow strip
section_title(dash, "SOS STATE", PURPLE)
STATE_COLOURS = {"NORMAL": CYAN, "TRIGGERED": RED, "COUNTDOWN": AMBER,
                 "ACTIVE": RED, "CANCELLED": PURPLE}
flow_frame = tk.Frame(dash, bg=BG)
flow_frame.pack(fill="x")
flow_labels = {}
for name in STATE_COLOURS:
    box = tk.Label(flow_frame, text=name, font=(MONO, -11, "bold"), fg=GREY,
                   bg=PANEL, padx=8, pady=5)
    box.pack(side="left", padx=(0, 6))
    flow_labels[name] = box

# Emergency contact cards (first 3 contacts)
section_title(dash, "EMERGENCY CONTACTS", PURPLE)
cards_frame = tk.Frame(dash, bg=BG)
cards_frame.pack(fill="x")
for i in range(min(3, len(contacts))):
    card = make_panel(cards_frame, BLUE)
    card.grid(row=0, column=i, padx=(0, 8), sticky="nsew")
    cards_frame.grid_columnconfigure(i, weight=1, uniform="cards")
    tk.Label(card, text="0" + str(i + 1) + "  " + contacts[i]["relation"].upper(),
             font=(MONO, -10, "bold"), fg=PURPLE, bg=PANEL).pack(anchor="w", padx=10, pady=(8, 0))
    tk.Label(card, text=contacts[i]["name"], font=(UI, -14, "bold"), fg=WHITE,
             bg=PANEL, wraplength=150, justify="left").pack(anchor="w", padx=10)
    tk.Label(card, text=contacts[i]["phone"], font=(MONO, -12), fg=GREY,
             bg=PANEL).pack(anchor="w", padx=10, pady=(0, 8))
if len(contacts) > 3:
    tk.Label(dash, text="+ " + str(len(contacts) - 3) + " more in contacts.txt",
             font=(MONO, -10), fg=GREY, bg=BG).pack(anchor="w", pady=(4, 0))

# GPS panel and alert panel side by side
row_frame = tk.Frame(dash, bg=BG)
row_frame.pack(fill="x", pady=(14, 0))
row_frame.grid_columnconfigure(0, weight=1, uniform="row")
row_frame.grid_columnconfigure(1, weight=1, uniform="row")

gps_panel = make_panel(row_frame, CYAN)
gps_panel.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
tk.Label(gps_panel, text="GPS LOCATION  [SIMULATED]", font=(MONO, -11, "bold"),
         fg=CYAN, bg=PANEL).pack(anchor="w", padx=10, pady=(8, 6))
lat_label = tk.Label(gps_panel, text=lat_text(), font=(MONO, -15, "bold"), fg=WHITE, bg=PANEL)
lat_label.pack(anchor="w", padx=10)
lon_label = tk.Label(gps_panel, text=lon_text(), font=(MONO, -15, "bold"), fg=WHITE, bg=PANEL)
lon_label.pack(anchor="w", padx=10)
tk.Label(gps_panel, text="Sample data - no GPS hardware used", font=(MONO, -10),
         fg=GREY, bg=PANEL).pack(anchor="w", padx=10, pady=(4, 0))
gps_time_label = tk.Label(gps_panel, text="Not updated yet", font=(MONO, -10),
                          fg=GREY, bg=PANEL)
gps_time_label.pack(anchor="w", padx=10)
gps_border = tk.Frame(gps_panel, bg=CYAN)          # 1-pixel neon border
gps_border.pack(anchor="w", padx=10, pady=(8, 10))
tk.Button(gps_border, text="UPDATE LOCATION", command=update_location,
          font=(MONO, -11, "bold"), fg=CYAN, bg=PANEL, activebackground=CYAN,
          activeforeground=BG, relief="flat", bd=0, padx=12, pady=4,
          cursor="hand2").pack(padx=1, pady=1)

STANDBY_TEXT = "STANDBY\nNo alerts prepared.\n\nAlerts appear here when\nSOS becomes active."
alert_panel = make_panel(row_frame, RED)
alert_panel.grid(row=0, column=1, sticky="nsew")
tk.Label(alert_panel, text="ALERTS  [DEMO MODE]", font=(MONO, -11, "bold"),
         fg=RED, bg=PANEL).pack(anchor="w", padx=10, pady=(8, 6))
alert_label = tk.Label(alert_panel, text=STANDBY_TEXT, font=(MONO, -11), fg=GREY,
                       bg=PANEL, justify="left", anchor="nw")
alert_label.pack(anchor="w", padx=10, pady=(0, 8))

# Event log
section_title(dash, "EVENT LOG", PURPLE)
log_border = make_panel(dash, BLUE)
log_border.pack(fill="x")
log_box = tk.Text(log_border, height=9, width=64, bg="#060a16", fg=WHITE,
                  font=(MONO, -11), relief="flat", bd=0, padx=8, pady=6,
                  state="disabled", wrap="word")
log_box.pack(fill="x")
log_box.tag_config("time", foreground=CYAN)

tk.Label(dash, text="Battery, network, GPS and alerts are SIMULATED. "
         "No real calls, SMS or internet are used.",
         font=(MONO, -10), fg=GREY, bg=BG).pack(anchor="w", pady=(8, 0))

# ---------- START ----------
draw_watch_body()
draw_normal_screen()
set_state("NORMAL")
root.protocol("WM_DELETE_WINDOW", close_app)
log_event("Application started - " + str(len(contacts)) + " contacts loaded")
heartbeat()
root.mainloop()