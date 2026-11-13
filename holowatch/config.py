"""Shared constants: palette, dimensions, layout numbers."""

# --- palette (0..1 RGB) ---------------------------------------------------
CYAN = (0.00, 0.90, 1.00)
BLUE = (0.10, 0.45, 1.00)
ICE = (0.75, 0.97, 1.00)
AMBER = (1.00, 0.72, 0.20)
GREEN = (0.20, 1.00, 0.60)
RED = (1.00, 0.18, 0.25)
MAGENTA = (1.00, 0.30, 0.85)

# --- watch case dimensions (model units) ----------------------------------
CASE_HALF_W = 1.70      # x
CASE_HALF_H = 2.00      # z (up)
CASE_HALF_T = 0.45      # y (depth, screen faces -y)
CASE_RADIUS = 0.95
SCREEN_INSET = 0.36

SCREEN_PX = (288, 352)  # texture size of the watch display

# --- scene layout ---------------------------------------------------------
WATCH_Z = 0.4           # hover height of watch centre
PLATFORM_Z = -5.0
CAM_DIST_DEFAULT = 24.0
CAM_DIST_MIN = 9.0
CAM_DIST_MAX = 46.0
CAM_ELEV_DEG = 8.0
CAM_TARGET_Z = -0.6

WINDOW_TITLE = "SmartWatch X - Holographic Projection Lab"

# floating label anchor positions (world space, relative to the hover height)
LABEL_POS = [(-4.3, 0, 3.0), (4.3, 0, 3.0), (-4.5, 0, 0.3), (4.5, 0, 0.3), (-4.3, 0, -2.6), (4.3, 0, -2.6)]
