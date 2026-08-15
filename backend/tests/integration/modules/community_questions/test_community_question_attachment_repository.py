"""Integration tests for `SqlAlchemyCommunityQuestionAttachmentRepository`
against a real PostgreSQL instance — `document_id` references a real
`medical_documents` row, per this module's own "reuse the existing File
module" reference-only attachment design."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_questions._helpers import (
    persist_document,
    persist_org_user_community,
    persist_patient,
    persist_topic,
)

from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionAttachment,
)
from app.modules.community_questions.domain.value_objects import QuestionId, QuestionTitle
from app.modules.community_questions.infrastructure.repositories import (
    SqlAlchemyCommunityQuestionAttachmentRepository,
    SqlAlchemyCommunityQuestionRepository,
)


async def _persist_question(
    db_session: AsyncSession,
    *,
    community_id: object,
    organization_id: object,
    author_id: object,
    primary_topic_id: object,
) -> CommunityQuestion:
    questions_repo = SqlAlchemyCommunityQuestionRepository(db_session)
    question = CommunityQuestion.create(
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=author_id,  # type: ignore[arg-type]
        primary_topic_id=primary_topic_id,  # type: ignore[arg-type]
        title=QuestionTitle("Title"),
        body="Body",
    )
    await questions_repo.add(question)
    await db_session.commit()
    return question


class TestCommunityQuestionAttachmentRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        patient = await persist_patient(db_session, organization_id=organization.id)
        document = await persist_document(
            db_session, organization_id=organization.id, patient_id=patient.id, user_id=user.id
        )
        repo = SqlAlchemyCommunityQuestionAttachmentRepository(db_session)
        attachment = CommunityQuestionAttachment.create(
            question_id=QuestionId(question.id), document_id=document.id
        )

        await repo.add(attachment)
        await db_session.commit()

        reloaded = await repo.get_by_id(attachment.id)
        assert reloaded is not None
        assert reloaded.question_id.value == question.id
        assert reloaded.document_id == document.id

    async def test_get_by_id_returns_none_for_unknown_attachment(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityQuestionAttachmentRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_remove_deletes_the_attachment(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        patient = await persist_patient(db_session, organization_id=organization.id)
        document = await persist_document(
            db_session, organization_id=organization.id, patient_id=patient.id, user_id=user.id
        )
        repo = SqlAlchemyCommunityQuestionAttachmentRepository(db_session)
        attachment = CommunityQuestionAttachment.create(
            question_id=QuestionId(question.id), document_id=document.id
        )
        await repo.add(attachment)
        await db_session.commit()

        await repo.remove(attachment.id)
        await db_session.commit()

        assert await repo.get_by_id(attachment.id) is None


class TestCommunityQuestionAttachmentQueries:
    async def test_list_by_question_returns_added_attachments(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        patient = await persist_patient(db_session, organization_id=organization.id)
        document = await persist_document(
            db_session, organization_id=organization.id, patient_id=patient.id, user_id=user.id
        )
        repo = SqlAlchemyCommunityQuestionAttachmentRepository(db_session)
        attachment = CommunityQuestionAttachment.create(
            question_id=QuestionId(question.id), document_id=document.id
        )
        await repo.add(attachment)
        await db_session.commit()

        results = await repo.list_by_question(question.id)
        assert [a.document_id for a in results] == [document.id]

    async def test_is_assigned_true_when_present(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        patient = await persist_patient(db_session, organization_id=organization.id)
        document = await persist_document(
            db_session, organization_id=organization.id, patient_id=patient.id, user_id=user.id
        )
        repo = SqlAlchemyCommunityQuestionAttachmentRepository(db_session)
        attachment = CommunityQuestionAttachment.create(
            question_id=QuestionId(question.id), document_id=document.id
        )
        await repo.add(attachment)
        await db_session.commit()

        assert await repo.is_assigned(question.id, document.id) is True

    async def test_is_assigned_false_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityQuestionAttachmentRepository(db_session)
        assert await repo.is_assigned(uuid4(), uuid4()) is False
