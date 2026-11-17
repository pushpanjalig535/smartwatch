# SmartWatch X - Unified Holographic Projection Lab

An interactive 3D holographic smartwatch platform in Python (**Panda3D + NumPy + Pillow + SQLite**).
All subsystem modules (**3D Holographic Watch**, **DORA Contactless Payments**, **Stem Cell Regeneration Lab**, and **Neon SOS Emergency Dispatch**) are merged into one unified platform.

> All health, fitness, GPS, and payment transactions are **simulated demo data** and are labelled as such.

---

## 🌟 Unified Architecture

The smartwatch OS now includes **7 interactive screens** accessible from the 3D watch face, bottom navigation bar, or number keys `1`-`7`:

1. **HOME**: Clock, live seconds, date, weather forecast, battery level, and interactive quick-jump tiles.
2. **HEALTH**: Beating heart animation, real-time dynamic ECG strip, heart rate (BPM), SpO2, skin temperature, stress levels, and HRV.
3. **FITNESS**: Activity radial rings (calories, distance, active minutes), daily 10,000 steps progress tracker.
4. **PAY (DORA Contactless Payments)**:
   - Live wallet balance (Rs. 500.00 demo balance).
   - Tap-to-Pay (Rs. 250) and QR Payment generators.
   - 4-digit PIN authentication pad (`1234`) with instant approval/decline notifications.
   - Transaction log history.
5. **BIO (Stem Cell & Bio-Regenerative Simulator)**:
   - Real-time animated cellular membrane, pulsing nucleus, and chemical receptor visualization.
   - Multi-lineage cellular differentiation: Stem Cell (pluripotent) -> Neuron (NEUROD1) -> Muscle Myocyte (MYOD1) -> Erythrocyte (GATA1).
   - Interactive cycling and differentiation progress monitoring.
6. **ALERTS**: Notifications cards for messages, phone calls, and hydration/posture reminders with tap-to-read states.
7. **SOS (Neon Emergency Dispatch System)**:
   - Emergency contacts loaded from `neon_sos/contacts.txt`.
   - 4-second safety countdown with tap-to-cancel safeguard.
   - Simulated GPS beacon (`12.9716° N, 77.5946° E`).
   - Automated dispatch logging to `neon_sos/sos_log.txt` and transmission simulation to `neon_sos/sos_outbox.txt`.

---

## 🚀 Running the Project

### Prerequisites
Python 3.9 - 3.12 with OpenGL 2.1+

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Modes of Execution

```bash
# 1. Run the Full Unified 3D SmartWatch Simulation
python main.py

# 2. Skip cinematic intro directly into the watch
python main.py --skip-intro

# 3. Companion sub-service modes
python main.py --mode=sos       # Standalone Neon SOS emergency console
python main.py --mode=cells     # Standalone Stem Cell visualizer GUI
python main.py --mode=pay-api   # Run DORA FastAPI REST backend on port 8000
```

---

## 🎮 Controls

| Action | Input |
|---|---|
| Rotate watch 360° | Left-drag (release = inertia) |
| Zoom | Mouse wheel |
| Interact with watch screen | Click screen directly (tap PIN pad, pay buttons, cell cycle, SOS) |
| Switch screens (1 - 7) | Bottom bar buttons, keys `1` to `7`, or `←` / `→` |
| Pause / resume rotation | `Space` |
| Projection on / off | `P` |
| Wireframe / Particles / Scanning | `W` / `T` / `S` |
| X-ray (internals view) | `X` |
| Disassemble / reassemble | `E` |
| 360° inspection tour | `I` |
| Reset camera & watch | `R` |
| Skip intro / hide HUD / bloom | `Enter` / `H` / `B` |

---

## 🧪 Testing

Run test verification suite:
```bash
python tests/test_core.py
```
