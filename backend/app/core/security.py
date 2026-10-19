"""Hash password (argon2) dan pembuatan/verifikasi JWT (masterplan 9.3)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash

from app.config import settings

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]

_password_hash = PasswordHash.recommended()  # argon2id

# Hash tetap untuk menyamakan waktu verifikasi saat username tidak ditemukan,
# sehingga penyerang tidak bisa menebak username valid dari selisih waktu respons.
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def _secret() -> str:
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET belum diisi atau kurang dari 32 karakter.")
    return settings.jwt_secret


def create_token(user_id: uuid.UUID, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.jwt_access_ttl_minutes)
        if token_type == "access"
        else timedelta(days=settings.jwt_refresh_ttl_days)
    )
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> uuid.UUID:
    """Kembalikan user_id dari token yang sah. Melempar jwt.InvalidTokenError bila tidak sah."""
    payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM], options={"require": ["sub", "exp", "type"]})
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("Jenis token tidak sesuai.")
    return uuid.UUID(payload["sub"])
