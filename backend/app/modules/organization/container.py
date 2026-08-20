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

**Self-service registration addendum** — `build_organization_facade` now
also wires `CreateOrganization` behind `OrganizationFacade`'s new
`OrganizationProvisioningPort` (see `public/interfaces.py`'s own
docstring), so `app.modules.authentication.application.use_cases
.register_user.RegisterUser` can provision a tenant for a brand new user
through this module's public surface only, never its internals.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import get_event_bus
from app.modules.organization.application.services.organization_query_service import (
    OrganizationQueryService,
)
from app.modules.organization.application.use_cases.create_organization import CreateOrganization
from app.modules.organization.infrastructure.repositories import (
    SqlAlchemyOrganizationRepository,
    SqlAlchemyOrganizationSettingsRepository,
)
from app.modules.organization.public.facade import OrganizationFacade
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


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
    create_organization_use_case = CreateOrganization(
        organization_repository=organization_repository,
        organization_settings_repository=organization_settings_repository,
        unit_of_work=SqlAlchemyUnitOfWork(session, event_bus=get_event_bus()),
    )

    return OrganizationFacade(
        query_service=query_service, create_organization_use_case=create_organization_use_case
    )
