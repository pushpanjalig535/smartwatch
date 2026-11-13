"""SmartWatch X - Holographic Projection Lab.

Run:  python main.py            (full cinematic startup)
      python main.py --skip-intro
      python main.py --fullscreen --bloom
"""
import argparse
from panda3d.core import loadPrcFileData


def main():
    ap = argparse.ArgumentParser(description="Holographic smartwatch simulation (Panda3D)")
    ap.add_argument("--skip-intro", action="store_true", help="skip the cinematic startup animation")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--size", default="1366x768", help="window size, e.g. 1600x900")
    ap.add_argument("--bloom", action="store_true", help="enable optional shader bloom (needs shader support)")
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    w, h = args.size.lower().split("x")
    loadPrcFileData("", f"""
window-title SmartWatch X - Holographic Projection Lab
win-size {w} {h}
fullscreen {1 if args.fullscreen else 0}
sync-video 1
framebuffer-multisample 1
multisamples 4
text-encoding utf8
notify-level warning
""")
    from holowatch.app import HoloApp
    HoloApp(skip_intro=args.skip_intro, bloom=args.bloom, audio=not args.no_audio).run()


if __name__ == "__main__":
    main()
