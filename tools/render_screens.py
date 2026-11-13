"""Render every watch screen to a contact sheet (headless, Pillow only).

    python tools/render_screens.py [out.png]
"""
import sys, os
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from holowatch.screen import WatchScreen, PAGES, W, H
from holowatch.telemetry import Telemetry

out = sys.argv[1] if len(sys.argv) > 1 else "screens.png"
tel, scr = Telemetry(), Telemetry and WatchScreen()
for _ in range(240):
    tel.update(1 / 60)
sheet = Image.new("RGB", ((W + 10) * len(PAGES), H + 10), (0, 0, 0))
for i in range(len(PAGES)):
    scr.set_page(i)
    if i == 4:
        scr.trigger_sos()
    for _ in range(30):
        scr.update(1 / 30)
        tel.update(1 / 30)
    im = scr.render(tel)
    bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
    sheet.paste(Image.alpha_composite(bg, im).convert("RGB"), (5 + i * (W + 10), 5))
sheet.save(out)
print("saved", out)
