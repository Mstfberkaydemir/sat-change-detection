"""Şifre özetleme (PBKDF2-SHA256, yalnızca standart kütüphane) ve JWT üretme/çözme.

passlib/bcrypt yerine standart kütüphane kullanıldı: sürüm uyumsuzluğu sorunları yaşanmaz.
"""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 600_000  # OWASP 2023 önerisi (PBKDF2-HMAC-SHA256)


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_b64, hash_b64 = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _b64d(salt_b64), int(iters))
        return hmac.compare_digest(dk, _b64d(hash_b64))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, secret_key: str, algorithm: str, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, secret_key: str, algorithm: str) -> Optional[str]:
    """Geçerliyse 'sub' (kullanıcı id'si, str) döndürür; süresi dolmuş/bozuk ise None."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None
