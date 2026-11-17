import sys
import os

# Robust path resolution for Vercel Serverless environment
# Check current directory and parent directory for backend
curr_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(curr_dir)

candidates = [
    os.path.join(curr_dir, "backend"),
    os.path.join(curr_dir, "dora-payments", "backend"),
    os.path.join(parent_dir, "backend"),
    os.path.join(parent_dir, "dora-payments", "backend"),
    os.path.join(os.getcwd(), "backend"),
    os.path.join(os.getcwd(), "dora-payments", "backend"),
]

for c in candidates:
    if os.path.exists(c) and c not in sys.path:
        sys.path.insert(0, c)

try:
    from app.main import app
except Exception as e:
    # Diagnostic fallback so runtime errors are visible instead of silent 500 crash
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="DORA Fallback")
    @app.get("/{rest_of_path:path}")
    def fallback_catchall(rest_of_path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": "DORA initialization failed",
                "details": str(e),
                "sys_path": sys.path[:5],
                "cwd": os.getcwd()
            }
        )
