"""Integration tests for `SqlAlchemyOrganizationSettingsRepository` and the
one-to-one `organization_id` uniqueness constraint, against a real
PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Organization, OrganizationSettings
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import (
    SqlAlchemyOrganizationRepository,
    SqlAlchemyOrganizationSettingsRepository,
)


def _unique_code() -> str:
    return f"ORG-{uuid4().hex[:12].upper()}"


async def _persist_organization(db_session: AsyncSession) -> Organization:
    org_repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(_unique_code()),
        name="Settings Test Org",
        type=OrganizationType.CLINIC,
    )
    await org_repo.add(organization)
    await db_session.commit()
    return organization


class TestOrganizationSettingsRoundTrip:
    async def test_save_and_reload_preserves_jsonb_fields(self, db_session: AsyncSession) -> None:
        organization = await _persist_organization(db_session)
        repo = SqlAlchemyOrganizationSettingsRepository(db_session)

        settings = OrganizationSettings.create_default(organization_id=organization.id)
        settings.update(
            working_hours={"monday": {"open": "09:00", "close": "17:00"}},
            appointment_duration_minutes=45,
            feature_flags={"ai_scribe": True, "telehealth": False},
            ai_settings={"enabled": True, "model": "gemini-2.5-pro"},
            notification_settings={"email_enabled": True},
        )
        await repo.add(settings)
        await db_session.commit()

        reloaded = await repo.get_by_organization_id(organization.id)
        assert reloaded is not None
        assert reloaded.working_hours == {"monday": {"open": "09:00", "close": "17:00"}}
        assert reloaded.appointment_duration_minutes == 45
        assert reloaded.feature_flags == {"ai_scribe": True, "telehealth": False}
        assert reloaded.ai_settings == {"enabled": True, "model": "gemini-2.5-pro"}
        assert reloaded.notification_settings == {"email_enabled": True}

    async def test_get_by_organization_id_returns_none_when_absent(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyOrganizationSettingsRepository(db_session)
        assert await repo.get_by_organization_id(uuid4()) is None


class TestOneToOneConstraint:
    async def test_second_settings_row_for_same_organization_violates_db_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await _persist_organization(db_session)
        repo = SqlAlchemyOrganizationSettingsRepository(db_session)

        first = OrganizationSettings.create_default(organization_id=organization.id)
        await repo.add(first)
        await db_session.commit()

        second = OrganizationSettings.create_default(organization_id=organization.id)
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
