"""
FastAPI dependencies for authentication and role-based access control.
"""

from typing import List

from fastapi import Depends, HTTPException, status

from app.models.user import RoleEnum, User
from app.services.auth_service import get_current_user


class RoleChecker:
    """
    Usage:
        @router.get(
            "/admin",
            dependencies=[Depends(RoleChecker([RoleEnum.ADMIN]))]
        )
    """

    def __init__(self, allowed_roles: List[RoleEnum]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user