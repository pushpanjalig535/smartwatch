"""Merged services for SmartWatch X: Payments, SOS Dispatch, and Cellular Regeneration."""
from __future__ import annotations
import os
import datetime
import random
import math
from typing import List, Dict, Any

FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTACTS_FILE = os.path.join(FOLDER, "neon_sos", "contacts.txt")
LOG_FILE = os.path.join(FOLDER, "neon_sos", "sos_log.txt")
OUTBOX_FILE = os.path.join(FOLDER, "neon_sos", "sos_outbox.txt")

# Default coordinates if GPS simulated
BASE_LAT = 12.97160
BASE_LON = 77.59460


# =====================================================================
# 1. SOS Dispatcher & Contact Manager
# =====================================================================
class EmergencyService:
    def __init__(self):
        self.contacts: List[Dict[str, str]] = self.load_contacts()
        self.lat = BASE_LAT
        self.lon = BASE_LON

    def load_contacts(self) -> List[Dict[str, str]]:
        contacts = []
        if os.path.exists(CONTACTS_FILE):
            try:
                with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = [p.strip() for p in line.split(",")]
                            name = parts[0] if len(parts) > 0 else "Emergency"
                            phone = parts[1] if len(parts) > 1 else "Unknown"
                            rel = parts[2] if len(parts) > 2 else "Contact"
                            contacts.append({"name": name, "phone": phone, "relation": rel})
            except Exception:
                pass
        if not contacts:
            contacts = [
                {"name": "Contact One", "phone": "+910000000001", "relation": "Parent"},
                {"name": "Campus Security", "phone": "+910000000003", "relation": "Security"}
            ]
        return contacts

    def log(self, message: str):
        now_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        line = f"{now_str} - {message}\n"
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def dispatch_alert(self) -> str:
        # Slight GPS drift to simulate live movement
        self.lat = BASE_LAT + random.uniform(-0.0005, 0.0005)
        self.lon = BASE_LON + random.uniform(-0.0005, 0.0005)
        now_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        out = [f"\n{now_str} - SIMULATED SOS ALERT"]
        out.append(f"Location (simulated): LAT  {self.lat:.5f} N, LON  {self.lon:.5f} E")
        for c in self.contacts:
            out.append(f"To: {c['name']} ({c['phone']}) [{c['relation']}]")
            out.append(f"Message: SOS! Emergency assistance needed. Simulated location: {self.lat:.5f}, {self.lon:.5f}")
            out.append("Transmitted: NO - simulation only")

        try:
            os.makedirs(os.path.dirname(OUTBOX_FILE), exist_ok=True)
            with open(OUTBOX_FILE, "a", encoding="utf-8") as f:
                f.write("\n".join(out) + "\n")
        except Exception:
            pass

        self.log(f"SOS ACTIVATED - simulated alerts dispatched to {len(self.contacts)} contacts")
        return f"{len(self.contacts)} CONTACTS ALERTED"


# =====================================================================
# 2. Secure Contactless Payment Service
# =====================================================================
class PaymentEngine:
    def __init__(self):
        self.balance_paise = 50000  # ₹500.00 demo balance
        self.pin = "1234"
        self.transactions: List[Dict[str, Any]] = [
            {"merchant": "Cyber Cafe", "amount_paise": 15000, "status": "SUCCESS", "time": "10:14"},
            {"merchant": "Transit Metro", "amount_paise": 4000, "status": "SUCCESS", "time": "08:30"}
        ]
        self.selected_amount_paise = 25000  # ₹250.00 default quick pay
        self.auth_state = "IDLE"  # IDLE | PIN_ENTRY | PROCESSING | APPROVED | DECLINED
        self.entered_pin = ""
        self.message = ""

    @property
    def balance_display(self) -> str:
        return f"Rs. {self.balance_paise / 100:.2f}"

    def reset_flow(self):
        self.auth_state = "IDLE"
        self.entered_pin = ""
        self.message = ""

    def start_payment(self, amount_paise: int = 25000):
        self.selected_amount_paise = amount_paise
        self.entered_pin = ""
        self.auth_state = "PIN_ENTRY"
        self.message = "ENTER 4-DIGIT PIN"

    def enter_digit(self, digit: str) -> bool:
        if self.auth_state != "PIN_ENTRY":
            return False
        if len(self.entered_pin) < 4:
            self.entered_pin += digit
        if len(self.entered_pin) == 4:
            return self.verify_and_pay()
        return False

    def backspace_digit(self):
        if self.entered_pin:
            self.entered_pin = self.entered_pin[:-1]

    def verify_and_pay(self) -> bool:
        if self.entered_pin == self.pin:
            if self.balance_paise >= self.selected_amount_paise:
                self.balance_paise -= self.selected_amount_paise
                self.auth_state = "APPROVED"
                now = datetime.datetime.now().strftime("%H:%M")
                self.transactions.insert(0, {
                    "merchant": "QuickPay NFC",
                    "amount_paise": self.selected_amount_paise,
                    "status": "SUCCESS",
                    "time": now
                })
                self.message = f"APPROVED: Rs. {self.selected_amount_paise/100:.2f}"
                return True
            else:
                self.auth_state = "DECLINED"
                self.message = "INSUFFICIENT FUNDS"
                return False
        else:
            self.auth_state = "DECLINED"
            self.message = "INVALID PIN"
            self.entered_pin = ""
            return False


# =====================================================================
# 3. Cellular Health & Regeneration Simulator
# =====================================================================
class BioCellSimulator:
    CELL_TYPES = {
        0: {"name": "Stem Cell", "type": "stem", "signal": "OCT4 / SOX2", "color": (34, 211, 238), "target": "Pluripotent Base"},
        1: {"name": "Neuron Cell", "type": "neuron", "signal": "NGF + Retinoic", "color": (167, 139, 250), "target": "Neural Cortex"},
        2: {"name": "Muscle Myocyte", "type": "muscle", "signal": "FGF / IGF-1", "color": (251, 113, 133), "target": "Cardiac Tissue"},
        3: {"name": "Erythrocyte", "type": "blood", "signal": "EPO Signal", "color": (248, 113, 113), "target": "Vascular Oxygenation"}
    }

    def __init__(self):
        self.mode = 0  # 0: stem, 1: neuron, 2: muscle, 3: blood
        self.progress = 0.85
        self.cycle_time = 0.0

    def next_cell_type(self):
        self.mode = (self.mode + 1) % len(self.CELL_TYPES)
        self.progress = 0.0

    def update(self, dt: float):
        self.cycle_time += dt
        if self.progress < 1.0:
            self.progress = min(1.0, self.progress + dt * 0.4)

    @property
    def current(self) -> Dict[str, Any]:
        return self.CELL_TYPES[self.mode]
