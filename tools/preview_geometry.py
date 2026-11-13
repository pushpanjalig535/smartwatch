"""Headless software preview of the watch geometry (NumPy + Pillow only).

    python tools/preview_geometry.py [out.png] [xray]
Renders front / side / back / top views as neon wireframes.
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from holowatch.watch_model import build_watch
from holowatch.mesh import rot_x, rot_z


def render(parts, heading, pitch, size=(420, 520), xray=False, scale=34):
    img = Image.new("RGB", size, (2, 6, 14))
    d = ImageDraw.Draw(img)
    R = rot_x(pitch) @ rot_z(heading)
    cx, cy = size[0] / 2, size[1] / 2
    for p in parts:
        if p.kind == "internal" and not xray:
            continue
        v = p.mesh.verts.astype(float) @ R.T
        col = tuple(int(255 * c) for c in p.color)
        if xray and p.kind == "shell":
            col = tuple(c // 3 for c in col)
        for a, b in p.mesh.lines:
            # camera looks along +y; screen x = x, screen y = -z (perspective-free)
            d.line([(cx + v[a, 0] * scale, cy - v[a, 2] * scale),
                    (cx + v[b, 0] * scale, cy - v[b, 2] * scale)], fill=col, width=1)
    return img


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "preview.png"
    xray = "xray" in sys.argv
    parts = build_watch()
    views = [(0, 0), (90, 0), (180, 0), (0, 90)]
    tiles = [render(parts, h, p, xray=xray) for h, p in views]
    sheet = Image.new("RGB", (420 * 4, 520))
    for i, t in enumerate(tiles):
        sheet.paste(t, (420 * i, 0))
    sheet.save(out)
    print("saved", out)
