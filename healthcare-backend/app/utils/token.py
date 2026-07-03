"""
utils/token.py

JWT generation and verification for access + refresh tokens.

Every token carries a `type` claim ("access" or "refresh") so a refresh token
can never be replayed as an access token and vice versa — decoding alone isn't
enough to trust a token; the caller must also check its declared type.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from jose import jwt

from app.config import settings


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    """Short-lived token used to authenticate individual API requests."""
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "role": role,
        "type": TokenType.ACCESS.value,
        "iat": datetime.utcnow(),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, expires_days: Optional[int] = None) -> str:
    """Long-lived token used only to obtain new access tokens. Its hash is stored
    server-side (see models.RefreshToken) so it can be revoked before it expires.
    """
    expire = datetime.utcnow() + timedelta(
        days=expires_days if expires_days is not None else settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject,
        "type": TokenType.REFRESH.value,
        "iat": datetime.utcnow(),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Verify signature + expiry and return the payload. Raises jose.JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def is_token_type(payload: dict, expected: TokenType) -> bool:
    return payload.get("type") == expected.value
