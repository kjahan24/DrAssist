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

**RBAC extension** — a later task ("Implement the RBAC (Roles &
Permissions) module") found `Role`/`Permission`/`RolePermission`/
`UserRole` already fully implemented here (per the scope note above) and
extended them in place rather than forking a second, disconnected
permission system under a new `app.modules.rbac` package — see
`infrastructure/models.py`'s own note on this. It added: `Role.is_active`
plus the "inactive roles cannot be assigned" and "UserRole assignments
must preserve organization consistency" checks `AssignRoleToUser` was
missing (see that use case's own docstring); `Role.__post_init__`
enforcing "global system roles must have organization_id = NULL" /
"organization roles must belong to exactly one organization" (previously
unvalidated); `Permission.name`/`resource`/`action` (`resource`/`action`
derived from `code`, replacing the old `module` column — see
`domain/entities.py`); `CreatePermission` (no application-layer path to
create a `Permission` existed before); `DeleteRole`/`ActivateRole`/
`DeactivateRole` (none existed); and `RoleQueryService`/
`PermissionQueryService` behind two new public ports, `RoleQueryPort`/
`PermissionQueryPort`, for the Hospital Admin Portal / Super Admin
Portal / FHIR-mapping consumers this task's own Future Compatibility
section names. It deliberately does **not** build a `RevokeRoleFromUser`
use case (`RoleRepository.revoke_from_user` already exists and is
usable, but no application-layer use case wraps it yet — out of this
task's stated scope), any Doctor/Patient/Reception/Hospital Admin/Super
Admin Portal, any API authorization middleware, Audit Log, FHIR API, or
Family/Caregiver Access integration, or any HTTP endpoint (per this
task's explicit exclusions).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.authentication.application.services.permission_query_service import (
    PermissionQueryService,
)
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.application.services.role_query_service import RoleQueryService
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
    role_query_service = RoleQueryService(role_repository=role_repository)
    permission_query_service = PermissionQueryService(permission_repository=permission_repository)

    return AuthenticationFacade(
        user_repository=user_repository,
        user_session_repository=user_session_repository,
        permission_service=permission_service,
        role_query_service=role_query_service,
        permission_query_service=permission_query_service,
        secret_key=settings.backend.secret_key,
        algorithm=settings.jwt.algorithm,
    )
