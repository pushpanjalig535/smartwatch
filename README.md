# SmartWatch X - Holographic Projection Lab

An interactive 3D holographic smartwatch simulation in Python (**Panda3D + NumPy + Pillow**).
A real 3D smartwatch (case, glass dome, crown, button, curved strap with buckle, heart-rate sensor,
internal components) is projected above a glowing platform, with a cinematic startup, five
interactive watch screens and a futuristic control dashboard.

> All health / fitness values are **simulated demo data** and are labelled as such on screen.

## Install

Python 3.9 - 3.12, any OS with OpenGL 2.1+ (Windows / macOS / Linux).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Options: `--skip-intro`, `--fullscreen`, `--size 1600x900`, `--bloom` (optional shader glow), `--no-audio`.

## Controls

| Action | Input |
|---|---|
| Rotate watch 360 deg | Left-drag (release = inertia) |
| Zoom | Mouse wheel |
| Interact with the watch screen | Click it (it lights up); click nav dots / tiles / SOS / notification cards |
| Switch screens | Bottom bar, keys `1`-`5`, or `<-` / `->` |
| Pause / resume rotation | `Space` |
| Projection on / off | `P` or panel (hologram dissolves into particles and re-forms) |
| Wireframe / Particles / Scanning | `W` / `T` / `S` or panel |
| X-ray (internals) | `X` |
| Disassemble / reassemble | `E` |
| 360 inspection tour | `I` (any drag cancels) |
| Reset camera + watch | `R` |
| Skip intro / hide HUD ring / bloom | `Enter` / `H` / `B` |

Sliders: hologram brightness, rotation speed, projection size.

## What you will see

1. **Cinematic startup (~16 s)**: dark lab -> small platform ignites -> blue energy pulse -> rotating scan rings ->
   vertical beams -> ~1,500 particles swirl in and rebuild the watch (sampled from the real mesh) -> display
   powers on with a scan-wipe -> health screen activates -> **"SMARTWATCH HOLOGRAPHIC PROJECTION INITIALIZED"**.
2. **Hologram effects**: additive neon edges with halo, translucent faces, scan ring + scan-line sheet,
   light pulses racing around the case, data streams, rotating health-indicator rings, glitch/ghost distortion,
   floating live labels with connection lines, floor grid, CRT scanline overlay.
3. **Watch screens**: Home (clock, date, battery, weather, HR, steps), Health (beating heart, live ECG, BPM, SpO2,
   temperature, sleep), Fitness (animated rings, steps, calories, distance, workout timer), Notifications
   (messages, calls, reminders), SOS (countdown -> simulated alert; nothing is ever sent).

## Project layout

```
main.py                 entry point / CLI
holowatch/
  config.py             palette, dimensions, layout constants
  mesh.py               NumPy mesh toolkit (loft, box, cylinder, sampling)      [pure]
  watch_model.py        procedural smartwatch geometry + internals               [pure]
  telemetry.py          simulated health data, ECG generator                     [pure]
  timeline.py           startup timeline + steady-state levels                   [pure]
  particles.py          particle field, edge runners, data streams, link lines   [pure]
  screen.py             Pillow renderer + interaction for the 5 watch screens    [pure]
  gfx.py                Panda3D helpers (geometry from NumPy, dynamic buffers)
  scene.py              watch rig, platform, scanners, HUD, environment, labels
  ui.py                 DirectGui dashboard
  sfx.py                procedurally generated sound effects (no asset files)
  app.py                application: input, picking, animation, wiring
tests/test_core.py      unit tests for the pure modules  (python tests/test_core.py)
tests/smoke_headless.py runs the real app loop against a mocked Panda3D
tools/preview_geometry.py   headless wireframe preview of the watch (PNG)
tools/render_screens.py     headless render of all watch screens (PNG)
```

Rendering is fixed-function (unlit, additive blending) - no custom shaders - so it is robust across GPUs.

## Troubleshooting

- **No sound**: audio is optional; use `--no-audio` to silence warnings.
- **Window fails to open with multisampling**: edit `multisamples 4` in `main.py` to `0`.
- **Slow on integrated GPUs**: use a smaller window (`--size 1100x620`) and turn off Particles / Scanning.
- `--bloom` uses Panda3D's CommonFilters; if it prints "unsupported", just run without it.
