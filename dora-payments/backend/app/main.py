import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db import init_db
from app.api.errors import DoraPaymentException, dora_exception_handler, success_envelope
from app.api.routes_payments import router as payments_router
from app.api.routes_wallet import router as wallet_router
from app.api.routes_auth import router as auth_router

app = FastAPI(
    title="DORA Universal Payment Module",
    description="Simulated and pluggable payment service for DORA watch and hologram ecosystem.",
    version=settings.DORA_MODULE_VERSION
)

# Exception handling
app.add_exception_handler(DoraPaymentException, dora_exception_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception as e:
        print(f"[DB Warning] SQLite init failed (ignoring for serverless read path): {e}")

# DORA Module Integration Endpoints
@app.get("/health", summary="Health check endpoint for DORA orchestrator")
def health_check():
    return success_envelope({
        "status": "healthy",
        "service": settings.DORA_MODULE_NAME,
        "version": settings.DORA_MODULE_VERSION
    })

@app.get("/manifest", summary="DORA plug-in manifest definition")
def get_manifest():
    return success_envelope({
        "module_id": settings.DORA_MODULE_NAME,
        "version": settings.DORA_MODULE_VERSION,
        "display_modes": ["watch", "hologram"],
        "capabilities": [
            "wallet.balance",
            "wallet.topup",
            "payment.create",
            "payment.authorize",
            "payment.upi_qr",
            "payment.nfc_tap"
        ],
        "default_limits": {
            "max_per_txn_paise": settings.MAX_PER_TRANSACTION_LIMIT_PAISE,
            "daily_limit_paise": settings.DAILY_LIMIT_PAISE,
            "currency": "INR"
        }
    })

# API Routes
api_v1_prefix = "/api/v1"
app.include_router(payments_router, prefix=api_v1_prefix)
app.include_router(wallet_router, prefix=api_v1_prefix)
app.include_router(auth_router, prefix=api_v1_prefix)

# Serve Frontend static files if present
_candidates = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "dora-payments", "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend")),
]
frontend_dir = next((p for p in _candidates if os.path.exists(p)), None)

if frontend_dir and os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_frontend():
    if frontend_dir:
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
    return success_envelope({
        "status": "online",
        "service": settings.DORA_MODULE_NAME,
        "docs": "/docs",
        "api": "/api/v1"
    })
