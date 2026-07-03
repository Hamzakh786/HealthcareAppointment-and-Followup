"""
routers/auth.py

HTTP layer only — request/response shapes and status codes. All logic lives in
services/auth_service.py.
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.database import get_db
from app.models.user import User, RoleEnum
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register a new DOCTOR or PATIENT account. ADMIN accounts can't self-register."""
    return auth_service.register_user(db, payload)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    """Email + password login. Returns a short-lived access token and a longer-lived refresh token."""
    return auth_service.login(db, payload)


@router.post("/login/oauth", response_model=schemas.TokenResponse, include_in_schema=False)
def login_oauth_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password-flow form endpoint, so Swagger UI's 'Authorize' button works out of the box."""
    return auth_service.login(db, schemas.UserLogin(email=form_data.username, password=form_data.password))


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(payload: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid, unrevoked refresh token for a brand-new access/refresh pair."""
    return auth_service.refresh_access_token(db, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: schemas.LogoutRequest, db: Session = Depends(get_db)):
    """Revoke a refresh token, e.g. on user-initiated sign-out."""
    auth_service.logout(db, payload.refresh_token)


@router.post("/forgot-password", response_model=schemas.ForgotPasswordResponse)
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Starts the password-reset flow. Always returns the same message regardless of
    whether the email is registered, to avoid leaking which emails exist.
    """
    token = auth_service.forgot_password(db, payload.email)

    response = schemas.ForgotPasswordResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )
    # Dev convenience only: expose the raw token in the response so this flow is
    # testable without a real email provider wired up. Never do this in production.
    if token and not settings.is_production:
        response.reset_token = token
    return response


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """Complete the password-reset flow using the token issued by /forgot-password."""
    auth_service.reset_password(db, payload.token, payload.new_password)


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: User = Depends(auth_service.get_current_user)):
    """Return the currently authenticated user."""
    return current_user


@router.get("/admin-only", tags=["RBAC example"])
def admin_only_example(current_user: User = Depends(auth_service.require_roles(RoleEnum.ADMIN))):
    """Example endpoint demonstrating role-based access control — ADMIN only."""
    return {"message": f"Hello ADMIN {current_user.full_name}"}


@router.get("/doctor-or-admin-only", tags=["RBAC example"])
def doctor_or_admin_example(
    current_user: User = Depends(auth_service.require_roles(RoleEnum.DOCTOR, RoleEnum.ADMIN)),
):
    """Example endpoint demonstrating RBAC with multiple allowed roles."""
    return {"message": f"Hello {current_user.role.value} {current_user.full_name}"}
