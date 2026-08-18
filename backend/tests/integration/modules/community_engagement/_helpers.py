"""Shared setup helpers for Community Engagement module repository tests.

`votes.user_id`/`saved_content.user_id`/`topic_followers.user_id`/
`community_followers.user_id`/`doctor_followers.follower_user_id` and
`.followed_user_id` all require real, persisted `users` rows;
`organization_id` requires a real `organizations` row;
`topic_followers.topic_id` requires a real `medical_topics` row;
`community_followers.community_id` requires a real `communities` row.
`votes.target_id`/`saved_content.target_id` have deliberately no foreign
key at all (see `infrastructure/models.py`'s own docstring), so these
tests use arbitrary UUIDs for vote/save targets — no `community_posts`/
`community_questions`/`community_answers` rows are needed. Kept local to
this test package rather than in `app/`, matching the identical
`persist_organization`/`persist_user`/`persist_community`/`persist_topic`
sequence `tests.integration.modules.community_comments._helpers` already
established.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.community.domain.entities import Community
from app.modules.community.domain.value_objects import CommunityName, CommunitySlug
from app.modules.community.infrastructure.repositories import SqlAlchemyCommunityRepository
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from app.modules.medical_topics.infrastructure.repositories import SqlAlchemyMedicalTopicRepository
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
        name="Community Engagement Test Org",
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    await db_session.commit()
    return organization


async def persist_user(db_session: AsyncSession, *, organization_id: object) -> User:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"community-engagement-test-{unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Engagement",
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
        slug=CommunitySlug(f"engagement-{unique_suffix().lower()}"),
        name=CommunityName("Engagement Community"),
        created_by=created_by,  # type: ignore[arg-type]
    )
    await repo.add(community)
    await db_session.commit()
    return community


async def persist_topic(db_session: AsyncSession) -> MedicalTopic:
    repo = SqlAlchemyMedicalTopicRepository(db_session)
    topic = MedicalTopic.create(
        slug=TopicSlug(f"engagement-topic-{unique_suffix().lower()}"),
        name=TopicName("Engagement Topic"),
    )
    await repo.add(topic)
    await db_session.commit()
    return topic


async def persist_org_user(db_session: AsyncSession) -> tuple[Organization, User]:
    organization = await persist_organization(db_session)
    user = await persist_user(db_session, organization_id=organization.id)
    return organization, user
