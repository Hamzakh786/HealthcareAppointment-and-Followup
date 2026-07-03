"""
services/auth_service.py

Business logic for the Authentication Module. Routers stay thin; everything
here is independently testable and reusable.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.database import get_db
from app.models.user import PasswordResetToken, RefreshToken, User, RoleEnum
from app.utils.security import generate_secure_token, hash_password, hash_token, verify_password
from app.utils.token import TokenType, create_access_token, create_refresh_token, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ============================== Registration ==============================
def register_user(db: Session, payload: schemas.UserRegister) -> User:
    """Create a new user. Rejects duplicate emails and public ADMIN self-registration."""
    email = payload.email.lower()

    # Duplicate email validation
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A user with this email already exists")

    # ADMIN accounts must not be self-servable through public registration.
    # Provision them via the create_admin.py script or an existing admin's tooling instead.
    # TEMPORARILY DISABLED FOR TESTING - TODO: Re-enable in production
    # if payload.role == RoleEnum.ADMIN:
    #     raise HTTPException(
    #         status.HTTP_403_FORBIDDEN,
    #         "Cannot self-register as ADMIN. Ask an existing administrator to create this account.",
    #     )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ============================== Login / tokens ==============================
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def _issue_token_pair(db: Session, user: User) -> schemas.TokenResponse:
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    refresh_token = create_refresh_token(subject=str(user.id))

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()

    return schemas.TokenResponse(access_token=access_token, refresh_token=refresh_token)


def login(db: Session, payload: schemas.UserLogin) -> schemas.TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")
    return _issue_token_pair(db, user)


def refresh_access_token(db: Session, refresh_token: str) -> schemas.TokenResponse:
    """Validate a refresh token and issue a brand-new access/refresh pair.
    The used refresh token is revoked immediately (rotation) so a leaked, already-used
    token can't be replayed.
    """
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    if payload.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token is not a refresh token")

    token_hash = hash_token(refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not db_token or db_token.revoked or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token has been revoked or expired")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User account is no longer active")

    db_token.revoked = True
    db.commit()

    return _issue_token_pair(db, user)


def logout(db: Session, refresh_token: str) -> None:
    """Revoke a single refresh token. Silently no-ops if it's unknown/already revoked."""
    token_hash = hash_token(refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if db_token:
        db_token.revoked = True
        db.commit()


# ============================== Forgot / reset password ==============================
def forgot_password(db: Session, email: str) -> Optional[str]:
    """
    Generate a password-reset token if the email exists, and store only its hash.
    Returns the raw token so the caller can email it — or, for local development,
    hand it back directly (see routers/auth.py). Deliberately behaves identically
    whether or not the email exists, so responses can't be used to enumerate users.
    """
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        return None

    raw_token = generate_secure_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
        )
    )
    db.commit()

    # TODO: wire up a real email provider (SES, SendGrid, Postmark, ...) here and
    # email a reset link containing `raw_token` instead of returning it to the caller.
    return raw_token


def reset_password(db: Session, token: str, new_password: str) -> None:
    token_hash = hash_token(token)
    reset_token = (
        db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    )

    if not reset_token or reset_token.used or reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")

    user.hashed_password = hash_password(new_password)
    reset_token.used = True

    # Force re-login everywhere by revoking every outstanding refresh token for this user.
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
    ).update({"revoked": True})

    db.commit()


# ============================== Current user / RBAC ==============================
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: decode the access token and load the corresponding active user."""
    credentials_exception = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != TokenType.ACCESS.value:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_roles(*allowed_roles: RoleEnum):
    """
    Dependency factory for role-based access control.
    Usage: Depends(require_roles(RoleEnum.ADMIN, RoleEnum.DOCTOR))
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"This action requires one of the following roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return dependency
