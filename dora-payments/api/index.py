import sys
import os

curr = os.path.dirname(os.path.abspath(__file__))
# Check backend folders
for p in [
    os.path.join(curr, "backend"),
    os.path.join(curr, "..", "backend"),
    os.path.join(curr, "..", "dora-payments", "backend"),
    os.path.join(os.getcwd(), "backend"),
    os.path.join(os.getcwd(), "dora-payments", "backend")
]:
    abs_p = os.path.abspath(p)
    if os.path.exists(abs_p) and abs_p not in sys.path:
        sys.path.insert(0, abs_p)

from app.main import app
