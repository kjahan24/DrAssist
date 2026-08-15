"""Shared setup helpers for Community Questions module repository tests —
`community_questions.community_id`/`.organization_id`/`.author_id`/
`.primary_topic_id` all require real, persisted `communities`/
`organizations`/`users`/`medical_topics` rows (and `community_question_topics
.topic_id`/`community_question_attachments.document_id`/
`community_question_followers.user_id` require real `medical_topics`/
`medical_documents`/`users` rows) to satisfy their FKs. Kept local to this
test package rather than in `app/`, matching the identical
`persist_organization`/`persist_user`/... sequence
`tests.integration.modules.community_posts._helpers` already established.
"""

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.community.domain.entities import Community
from app.modules.community.domain.value_objects import CommunityName, CommunitySlug
from app.modules.community.infrastructure.repositories import SqlAlchemyCommunityRepository
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, StorageProvider
from app.modules.documents.domain.value_objects import Sha256Checksum
from app.modules.documents.infrastructure.repositories import SqlAlchemyMedicalDocumentRepository
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from app.modules.medical_topics.infrastructure.repositories import SqlAlchemyMedicalTopicRepository
from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientRepository
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


def unique_suffix() -> str:
    return uuid4().hex[:12].upper()


async def persist_organization(db_session: AsyncSession) -> Organization:
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{unique_suffix()}"),
        name="Community Questions Test Org",
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    await db_session.commit()
    return organization


async def persist_user(db_session: AsyncSession, *, organization_id: object) -> User:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"community-questions-test-{unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Question",
        last_name="Author",
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
        slug=CommunitySlug(f"oncology-{unique_suffix().lower()}"),
        name=CommunityName("Oncology"),
        created_by=created_by,  # type: ignore[arg-type]
    )
    await repo.add(community)
    await db_session.commit()
    return community


async def persist_topic(db_session: AsyncSession) -> MedicalTopic:
    repo = SqlAlchemyMedicalTopicRepository(db_session)
    topic = MedicalTopic.create(
        slug=TopicSlug(f"cardiology-{unique_suffix().lower()}"), name=TopicName("Cardiology")
    )
    await repo.add(topic)
    await db_session.commit()
    return topic


async def persist_document(
    db_session: AsyncSession, *, organization_id: object, patient_id: object, user_id: object
) -> MedicalDocument:
    repo = SqlAlchemyMedicalDocumentRepository(db_session)
    document = MedicalDocument.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        uploaded_by_user_id=user_id,  # type: ignore[arg-type]
        category=DocumentCategory.LAB_REPORT,
        title="Attachment Document",
        original_filename="attachment.pdf",
        stored_filename=f"{uuid4().hex}.pdf",
        mime_type="application/pdf",
        extension=".pdf",
        file_size_bytes=1024,
        storage_provider=StorageProvider.LOCAL,
        storage_path=f"community-questions-test/{uuid4().hex}.pdf",
        checksum_sha256=Sha256Checksum((uuid4().hex + uuid4().hex)[:64]),
        uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    await repo.add(document)
    await db_session.commit()
    return document


async def persist_patient(db_session: AsyncSession, *, organization_id: object) -> Patient:
    repo = SqlAlchemyPatientRepository(db_session)
    patient = Patient.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_number=f"PAT-{unique_suffix()}",
        first_name="Jane",
        last_name="Doe",
        gender=Gender.FEMALE,
        date_of_birth=date(1990, 1, 1),
    )
    await repo.add(patient)
    await db_session.commit()
    return patient


async def persist_org_user_community(
    db_session: AsyncSession,
) -> tuple[Organization, User, Community]:
    organization = await persist_organization(db_session)
    user = await persist_user(db_session, organization_id=organization.id)
    community = await persist_community(
        db_session, organization_id=organization.id, created_by=user.id
    )
    return organization, user, community
