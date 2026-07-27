"""Module composition root.

The one place `OrganizationQueryPort` gets bound to its concrete
implementation (`OrganizationFacade`), and repository interfaces get bound
to their SQLAlchemy implementations. Any future module's
`api/dependencies.py` calls `build_organization_facade(session)` rather
than constructing `OrganizationFacade` (or any repository) directly.

Scope note — this task builds the Organization module's **foundation**
only: `Organization`, `OrganizationSettings`, `Department` entities,
repositories, `CreateOrganization` (which provisions default settings
atomically), `UpdateOrganizationSettings`, `CreateDepartment`, and the
public query facade. It deliberately does **not** build any HTTP endpoint,
and does not modify the Authentication module or its tables — the
`organization_id` foreign key deferred on `users`/`roles`/`user_roles`/
`user_sessions`/`refresh_tokens` (see
`docs/database/08_migration_strategy.md §6` and the Authentication
migration's own docstring) remains deferred; adding it would mean
altering Authentication's schema, which is explicitly out of scope here.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.application.services.organization_query_service import (
    OrganizationQueryService,
)
from app.modules.organization.infrastructure.repositories import (
    SqlAlchemyOrganizationRepository,
    SqlAlchemyOrganizationSettingsRepository,
)
from app.modules.organization.public.facade import OrganizationFacade


def build_organization_facade(session: AsyncSession) -> OrganizationFacade:
    """Construct an `OrganizationFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    organization_repository = SqlAlchemyOrganizationRepository(session)
    organization_settings_repository = SqlAlchemyOrganizationSettingsRepository(session)

    query_service = OrganizationQueryService(
        organization_repository=organization_repository,
        organization_settings_repository=organization_settings_repository,
    )

    return OrganizationFacade(query_service=query_service)
