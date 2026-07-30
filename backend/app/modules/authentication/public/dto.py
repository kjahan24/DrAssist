"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape.
"""

from app.modules.authentication.application.dto import (
    AuthenticatedPrincipalDTO,
    PermissionSummaryDTO,
    RoleSummaryDTO,
    UserSummaryDTO,
)

__all__ = [
    "AuthenticatedPrincipalDTO",
    "PermissionSummaryDTO",
    "RoleSummaryDTO",
    "UserSummaryDTO",
]
