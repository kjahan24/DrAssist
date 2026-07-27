"""Enums owned by the Authentication module's domain.

Mirrors `user_status_enum` from `docs/database/01_identity_and_access.md`.
"""

from enum import StrEnum


class UserStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
