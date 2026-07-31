"""Shared setup helpers for HTTP-level (router) API tests — every test
needs a real, persisted `organizations` row (and often a `users` row) to
satisfy foreign keys and to build an `AuthenticatedPrincipalDTO` bound to
a real tenant. Mirrors the identical `persist_organization`/`persist_user`
sequence `tests.integration.modules.appointment._helpers` already
established for repository-layer tests — kept local to this test package
rather than centralized, matching that same per-package convention.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit_log.application.dto import RecordAuditLogInput
from app.modules.audit_log.application.use_cases.record_audit_log import RecordAuditLog
from app.modules.audit_log.container import build_record_audit_log_use_case
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.organization.domain.entities import Organization, OrganizationSettings
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import (
    SqlAlchemyOrganizationRepository,
    SqlAlchemyOrganizationSettingsRepository,
)
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


def unique_suffix() -> str:
    return uuid4().hex[:12].upper()


async def persist_organization(
    db_session: AsyncSession, *, name: str = "API Test Org"
) -> Organization:
    """Also persists a default `OrganizationSettings` row — mirroring
    `CreateOrganization`'s own one-transaction "always create both
    together" invariant (see `OrganizationSettings.create_default`'s own
    docstring for why there is no standalone "create settings" path).
    Without this, `GET/PATCH .../settings` 404s for every organization
    this helper creates."""
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{unique_suffix()}"),
        name=name,
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    settings_repo = SqlAlchemyOrganizationSettingsRepository(db_session)
    settings = OrganizationSettings.create_default(organization_id=organization.id)
    await settings_repo.add(settings)
    await db_session.commit()
    return organization


async def persist_user(db_session: AsyncSession, *, organization_id: object) -> User:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"api-test-{unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Front",
        last_name="Desk",
    )
    await user_repo.add(user)
    await db_session.commit()
    return user


async def record_audit_log(
    db_session: AsyncSession,
    *,
    organization_id: object,
    entity_type: str = "patient",
    entity_id: object | None = None,
    actor_user_id: object | None = None,
) -> object:
    use_case: RecordAuditLog = build_record_audit_log_use_case(db_session)
    output = await use_case.execute(
        RecordAuditLogInput(
            organization_id=organization_id,  # type: ignore[arg-type]
            entity_type=entity_type,
            entity_id=entity_id or uuid4(),  # type: ignore[arg-type]
            action=AuditAction.CREATE,
            source=AuditSource.API,
            actor_user_id=actor_user_id,  # type: ignore[arg-type]
        )
    )
    return output.audit_log_id
