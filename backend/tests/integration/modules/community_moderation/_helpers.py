"""Shared setup helpers for Community Moderation module repository tests.

`community_reports.organization_id`/`.community_id`/`.reporter_id`/
`.assigned_moderator_id`, `moderation_actions.organization_id`/
`.actor_id`, `moderation_restrictions.organization_id`/`.community_id`/
`.user_id`/`.issued_by`, and `doctor_verifications.doctor_id`/`.user_id`/
`.organization_id`/`.verifier_id` all require real, persisted
`organizations`/`users`/`communities`/`doctors` rows. `target_id` on
`community_reports`/`moderation_actions` has no foreign key at all (see
`infrastructure/models.py`'s own docstring), so these tests use arbitrary
UUIDs for report/action targets — no `community_posts`/etc. rows needed.
"""

from datetime import date
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.community.domain.entities import Community
from app.modules.community.domain.value_objects import CommunityName, CommunitySlug
from app.modules.community.infrastructure.repositories import SqlAlchemyCommunityRepository
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.infrastructure.repositories import SqlAlchemyDoctorRepository
from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


def unique_suffix() -> str:
    return uuid4().hex[:12].upper()


async def persist_organization(db_session: AsyncSession) -> Organization:
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{unique_suffix()}"),
        name="Community Moderation Test Org",
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    await db_session.commit()
    return organization


async def persist_user(db_session: AsyncSession, *, organization_id: object) -> User:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"community-moderation-test-{unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Moderation",
        last_name="User",
    )
    await user_repo.add(user)
    await db_session.commit()
    return user


async def persist_community(
    db_session: AsyncSession, *, organization_id: object, created_by: object | None = None
) -> Community:
    repo = SqlAlchemyCommunityRepository(db_session)
    community = Community.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        slug=CommunitySlug(f"moderation-{unique_suffix().lower()}"),
        name=CommunityName("Moderation Community"),
        created_by=created_by,  # type: ignore[arg-type]
    )
    await repo.add(community)
    await db_session.commit()
    return community


async def persist_doctor(
    db_session: AsyncSession, *, organization_id: object, user_id: object
) -> Doctor:
    repo = SqlAlchemyDoctorRepository(db_session)
    doctor = Doctor.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        user_id=user_id,  # type: ignore[arg-type]
        employee_id=f"EMP-{unique_suffix()}",
        joining_date=date(2020, 1, 1),
    )
    await repo.add(doctor)
    await db_session.commit()
    return doctor


async def persist_org_user(db_session: AsyncSession) -> tuple[Organization, User]:
    organization = await persist_organization(db_session)
    user = await persist_user(db_session, organization_id=organization.id)
    return organization, user


async def persist_org_user_community(
    db_session: AsyncSession,
) -> tuple[Organization, User, Community]:
    organization = await persist_organization(db_session)
    user = await persist_user(db_session, organization_id=organization.id)
    community = await persist_community(
        db_session, organization_id=organization.id, created_by=user.id
    )
    return organization, user, community
