"""
Authentication package initialization
"""

from app.auth.router import router
from app.auth.service import AuthService
from app.auth.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserProfile,
    UserUpdate,
    PasswordChange
)

__all__ = [
    "router",
    "AuthService",
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "UserProfile",
    "UserUpdate",
    "PasswordChange"
]
