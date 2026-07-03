"""
utils/security.py

- Password hashing uses pbkdf2_sha256 (via passlib) — faster than bcrypt but still secure
  for low-entropy user-chosen secrets.
- Refresh tokens and password-reset tokens are high-entropy random strings, not
  user-chosen, so they're hashed with SHA-256 instead of bcrypt: bcrypt's
  deliberate slowness buys nothing here (the tokens can't be brute-forced) and
  would just needlessly slow down every refresh/reset lookup.
"""
import hashlib
import secrets

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_secure_token(nbytes: int = 32) -> str:
    """Cryptographically secure, URL-safe random token (refresh/reset tokens)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """One-way SHA-256 hash of an opaque token, so raw tokens are never stored in the DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
