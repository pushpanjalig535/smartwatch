"""SmartWatch X - Holographic Projection Lab (Unified Edition).

Merges 3D Holographic Watch OS, DORA Contactless Payments,
Cellular Regeneration Simulator, and Neon SOS Emergency System.

Run:  python main.py                  (Full unified 3D holographic watch)
      python main.py --skip-intro     (Direct into watch interaction)
      python main.py --mode=sos       (Standalone Neon SOS console mode)
      python main.py --mode=cells     (Standalone Stem Cell simulator GUI)
      python main.py --mode=pay-api   (Start DORA Payment REST backend)
"""
import argparse
import sys
import subprocess
import os

def main():
    ap = argparse.ArgumentParser(description="SmartWatch X - Unified SmartWatch Platform")
    ap.add_argument("--skip-intro", action="store_true", help="skip the cinematic startup animation")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--size", default="1366x768", help="window size, e.g. 1600x900")
    ap.add_argument("--bloom", action="store_true", help="enable optional shader bloom (needs GPU support)")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--mode", default="watch", choices=["watch", "sos", "cells", "pay-api"],
                    help="Run watch (default 3D unified OS), or standalone companion modes")
    args = ap.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Standalone companion modes if requested
    if args.mode == "sos":
        print("[SmartWatch X] Launching standalone Neon SOS console...")
        sos_path = os.path.join(base_dir, "neon_sos", "sos_watch.py")
        subprocess.run([sys.executable, sos_path])
        return

    if args.mode == "cells":
        print("[SmartWatch X] Launching standalone Stem Cell Simulator...")
        cell_path = os.path.join(base_dir, "stem_cell_simulator", "stem_cell_simulator.py")
        subprocess.run([sys.executable, cell_path])
        return

    if args.mode == "pay-api":
        print("[SmartWatch X] Launching DORA Payment API on port 8000...")
        pay_dir = os.path.join(base_dir, "dora-payments")
        subprocess.run([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", "8000", "--reload"], cwd=pay_dir)
        return

    # Default: Unified 3D Holographic SmartWatch
    from panda3d.core import loadPrcFileData
    w, h = args.size.lower().split("x")
    loadPrcFileData("", f"""
window-title SmartWatch X - Holographic Projection Lab (Unified Platform)
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
