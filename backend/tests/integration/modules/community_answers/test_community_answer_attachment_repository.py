"""Integration tests for `SqlAlchemyCommunityAnswerAttachmentRepository`
against a real PostgreSQL instance — round-trip persistence,
`is_assigned`, the unique `(answer_id, document_id)` constraint, and hard
`remove()`.

`community_answer_attachments.answer_id`/`.document_id` are real foreign
keys (`-> community_answers.id`/`-> medical_documents.id`), so every
attachment here is created against an actual persisted `CommunityAnswer`
and `MedicalDocument`.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_answers._helpers import (
    persist_document,
    persist_org_user_community_question,
    persist_patient,
)

from app.modules.community_answers.domain.entities import CommunityAnswer, CommunityAnswerAttachment
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerId
from app.modules.community_answers.infrastructure.repositories import (
    SqlAlchemyCommunityAnswerAttachmentRepository,
    SqlAlchemyCommunityAnswerRepository,
)
from app.modules.documents.domain.entities import MedicalDocument


async def _persist_answer_and_document(
    db_session: AsyncSession,
) -> tuple[CommunityAnswer, MedicalDocument]:
    organization, user, community, topic, question = await persist_org_user_community_question(
        db_session
    )
    answers = SqlAlchemyCommunityAnswerRepository(db_session)
    answer = CommunityAnswer.create(
        question_id=question.id,
        community_id=community.id,
        organization_id=organization.id,
        topic_id=topic.id,
        author_id=user.id,
        body=AnswerBody("Body."),
    )
    await answers.add(answer)
    await db_session.commit()

    patient = await persist_patient(db_session, organization_id=organization.id)
    document = await persist_document(
        db_session, organization_id=organization.id, patient_id=patient.id, user_id=user.id
    )
    return answer, document


class TestCommunityAnswerAttachmentRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        answer, document = await _persist_answer_and_document(db_session)
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)
        attachment = CommunityAnswerAttachment.create(
            answer_id=AnswerId(answer.id), document_id=document.id
        )

        await repo.add(attachment)
        await db_session.commit()

        reloaded = await repo.get_by_id(attachment.id)
        assert reloaded is not None
        assert reloaded.id == attachment.id
        assert reloaded.answer_id.value == answer.id
        assert reloaded.document_id == document.id

    async def test_get_by_id_returns_none_for_unknown_attachment(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestCommunityAnswerAttachmentListByAnswer:
    async def test_lists_only_attachments_for_the_requested_answer(
        self, db_session: AsyncSession
    ) -> None:
        answer, document = await _persist_answer_and_document(db_session)
        other_answer, other_document = await _persist_answer_and_document(db_session)
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)
        mine = CommunityAnswerAttachment.create(
            answer_id=AnswerId(answer.id), document_id=document.id
        )
        not_mine = CommunityAnswerAttachment.create(
            answer_id=AnswerId(other_answer.id), document_id=other_document.id
        )
        await repo.add(mine)
        await repo.add(not_mine)
        await db_session.commit()

        results = await repo.list_by_answer(answer.id)
        ids = [a.id for a in results]
        assert mine.id in ids
        assert not_mine.id not in ids


class TestCommunityAnswerAttachmentIsAssigned:
    async def test_true_when_assigned(self, db_session: AsyncSession) -> None:
        answer, document = await _persist_answer_and_document(db_session)
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)
        attachment = CommunityAnswerAttachment.create(
            answer_id=AnswerId(answer.id), document_id=document.id
        )
        await repo.add(attachment)
        await db_session.commit()

        assert await repo.is_assigned(answer.id, document.id) is True

    async def test_false_when_not_assigned(self, db_session: AsyncSession) -> None:
        answer, document = await _persist_answer_and_document(db_session)
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)

        assert await repo.is_assigned(answer.id, document.id) is False

    async def test_duplicate_answer_document_pair_violates_the_unique_constraint(
        self, db_session: AsyncSession
    ) -> None:
        answer, document = await _persist_answer_and_document(db_session)
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)
        first = CommunityAnswerAttachment.create(
            answer_id=AnswerId(answer.id), document_id=document.id
        )
        await repo.add(first)
        await db_session.commit()

        second = CommunityAnswerAttachment.create(
            answer_id=AnswerId(answer.id), document_id=document.id
        )
        await repo.add(second)
        try:
            await db_session.commit()
            raised = False
        except Exception:  # noqa: BLE001 — asserting *a* DB constraint violation occurs
            raised = True
            await db_session.rollback()
        assert raised is True


class TestCommunityAnswerAttachmentRemove:
    async def test_removes_the_attachment(self, db_session: AsyncSession) -> None:
        answer, document = await _persist_answer_and_document(db_session)
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)
        attachment = CommunityAnswerAttachment.create(
            answer_id=AnswerId(answer.id), document_id=document.id
        )
        await repo.add(attachment)
        await db_session.commit()

        await repo.remove(attachment.id)
        await db_session.commit()

        assert await repo.get_by_id(attachment.id) is None

    async def test_removing_an_unknown_attachment_is_a_no_op(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityAnswerAttachmentRepository(db_session)
        await repo.remove(uuid4())
        await db_session.commit()
