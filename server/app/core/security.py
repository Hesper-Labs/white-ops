"""Security utilities: password hashing, JWT tokens, MFA (TOTP), API keys."""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token configuration
TOKEN_AUDIENCE = "whiteops-api"
TOKEN_ISSUER = "whiteops"
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ---- Password Hashing ----


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---- Password Strength Validation ----


def validate_password_strength(password: str) -> dict:
    """Validate password meets strength requirements.

    Requirements: min 12 chars, uppercase, lowercase, digit, special character.
    Returns dict with `valid` (bool) and `errors` (list[str]).
    """
    errors: list[str] = []

    if len(password) < 12:
        errors.append("Password must be at least 12 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        errors.append("Password must contain at least one special character.")

    return {"valid": len(errors) == 0, "errors": errors}


# ---- Access Tokens ----


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "iat": now,
        "aud": TOKEN_AUDIENCE,
        "iss": TOKEN_ISSUER,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=TOKEN_AUDIENCE,
        issuer=TOKEN_ISSUER,
    )


# ---- Refresh Tokens ----


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "aud": TOKEN_AUDIENCE,
        "iss": TOKEN_ISSUER,
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=TOKEN_AUDIENCE,
        issuer=TOKEN_ISSUER,
    )
    if payload.get("type") != "refresh":
        raise jwt.JWTError("Token is not a refresh token")
    return payload


# ---- TOTP / MFA ----


def generate_totp_secret() -> str:
    """Generate a new TOTP secret for MFA enrollment."""
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against the secret. Allows 1 window of drift."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ---- API Keys ----


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """Hash an API key for storage using SHA-256."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, hashed: str) -> bool:
    """Verify an API key against its stored hash."""
    return secrets.compare_digest(hash_api_key(key), hashed)
