import os
import tempfile
from pydantic_settings import BaseSettings
from typing import Literal

def _default_db_url():
    if os.environ.get("VERCEL"):
        # On Vercel serverless Linux, writable directory is tempfile.gettempdir()
        tmp = tempfile.gettempdir().replace("\\", "/")
        return f"sqlite:///{tmp}/dora_payments.db"
    return "sqlite:///./dora_payments.db"

class Settings(BaseSettings):
    DORA_ENV: str = "development"
    DORA_MODULE_NAME: str = "dora-payments"
    DORA_MODULE_VERSION: str = "0.1.0"
    SECRET_KEY: str = "dora-dev-secret-key-change-in-production-123456789"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = _default_db_url()

    # Money limits in paise (never float)
    MAX_PER_TRANSACTION_LIMIT_PAISE: int = 500000  # 5,000 INR
    DAILY_LIMIT_PAISE: int = 2000000              # 20,000 INR
    PAYMENT_TIMEOUT_SECONDS: int = 60

    # PIN security
    MAX_PIN_ATTEMPTS: int = 3
    PIN_LOCKOUT_MINUTES: int = 15

    # UI display
    DEFAULT_UI_MODE: Literal["watch", "hologram"] = "watch"
    WATCH_SCREEN_DIAMETER_PX: int = 240

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
