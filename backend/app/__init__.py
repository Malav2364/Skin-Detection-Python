"""
Application package initialization
"""

from app.config import get_settings, init_settings
from app.dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_any_role,
    get_optional_user,
    get_client_ip
)

__all__ = [
    "get_settings",
    "init_settings",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_any_role",
    "get_optional_user",
    "get_client_ip"
]
