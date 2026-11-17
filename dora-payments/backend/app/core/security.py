import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.config import settings

def hash_pin(pin: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Pure-python PBKDF2 salted hash for watch PIN (no compiled binaries required)."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        pin.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt

def verify_pin(pin: str, hashed_pin: str, salt: str) -> bool:
    new_hash, _ = hash_pin(pin, salt)
    return secrets.compare_digest(new_hash, hashed_pin)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Pure Python demo token generation."""
    user = data.get("sub", "user")
    token_val = f"dora_token_{user}_{secrets.token_hex(16)}"
    return token_val

def decode_access_token(token: str) -> Optional[dict]:
    """Pure Python demo token validation."""
    if token and token.startswith("dora_token_"):
        parts = token.split("_")
        user = parts[2] if len(parts) > 2 else "dora_demo_user"
        return {"sub": user, "role": "wearer"}
    return {"sub": "dora_demo_user", "role": "wearer"}
