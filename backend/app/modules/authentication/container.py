"""Module composition root.

The one place `PermissionCheckPort`/`UserQueryPort`/
`AccessTokenValidationPort` get bound to their concrete implementation
(`AuthenticationFacade`), and repository interfaces get bound to their
SQLAlchemy implementations. `app/api/deps.py` and any future module's
`api/dependencies.py` call `build_authentication_facade(session)` rather
than constructing `AuthenticationFacade` (or any repository) directly.

Scope note — this task builds the Authentication module's **foundation**
only: entities, repositories, RBAC administration (`CreateRole`,
`AssignPermissionToRole`, `AssignRoleToUser`), password hashing, JWT
encode/decode, and the token-validation path `get_current_user` needs.
It deliberately does **not** build `RegisterUser`/`AuthenticateUser`/
`RefreshAccessToken`/`RevokeSession` or any HTTP endpoint — those are a
follow-up task, per the brief this module was built against.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.infrastructure.repositories import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserSessionRepository,
)
from app.modules.authentication.public.facade import AuthenticationFacade


def build_authentication_facade(session: AsyncSession) -> AuthenticationFacade:
    """Construct an `AuthenticationFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    settings = get_settings()
    user_repository = SqlAlchemyUserRepository(session)
    role_repository = SqlAlchemyRoleRepository(session)
    permission_repository = SqlAlchemyPermissionRepository(session)
    user_session_repository = SqlAlchemyUserSessionRepository(session)

    permission_service = RbacPermissionService(
        role_repository=role_repository, permission_repository=permission_repository
    )

    return AuthenticationFacade(
        user_repository=user_repository,
        user_session_repository=user_session_repository,
        permission_service=permission_service,
        secret_key=settings.backend.secret_key,
        algorithm=settings.jwt.algorithm,
    )
