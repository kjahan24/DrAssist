"""Unit tests for `ManageQuestionAttachmentsService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_questions.application.dto import (
    AddQuestionAttachmentInput,
    RemoveQuestionAttachmentInput,
)
from app.modules.community_questions.application.services.manage_question_attachments_service import (  # noqa: E501
    ManageQuestionAttachmentsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.events import CommunityQuestionAttachmentAdded
from app.modules.community_questions.domain.exceptions import (
    DocumentNotFoundForQuestionError,
    DuplicateQuestionAttachmentError,
    InsufficientQuestionRoleError,
    QuestionAttachmentNotFoundError,
    QuestionNotFoundError,
)
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionAttachmentRepository,
    FakeCommunityQuestionRepository,
    FakeDocumentQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManageQuestionAttachmentsService,
        FakeCommunityQuestionRepository,
        FakeCommunityQuestionAttachmentRepository,
        FakeCommunityQueryPort,
        FakeDocumentQueryPort,
        FakeUnitOfWork,
    ]
):
    questions = FakeCommunityQuestionRepository()
    attachments = FakeCommunityQuestionAttachmentRepository()
    communities = FakeCommunityQueryPort()
    documents = FakeDocumentQueryPort()
    uow = FakeUnitOfWork()
    service = ManageQuestionAttachmentsService(
        question_attachment_repository=attachments,
        question_repository=questions,
        community_query_port=communities,
        document_query_port=documents,
        unit_of_work=uow,
    )
    return service, questions, attachments, communities, documents, uow


async def _seed_question(
    questions: FakeCommunityQuestionRepository, communities: FakeCommunityQueryPort
) -> CommunityQuestion:
    question = CommunityQuestion.create(
        community_id=uuid4(),
        organization_id=uuid4(),
        author_id=uuid4(),
        primary_topic_id=uuid4(),
        title=QuestionTitle("Title"),
        body="Body",
    )
    await questions.add(question)
    communities.add_community(make_community_summary(community_id=question.community_id))
    return question


class TestAddAttachment:
    async def test_author_adds_an_attachment(self) -> None:
        service, questions, attachments, communities, documents, _ = _seeded()
        question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)

        summary = await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                document_id=document_id,
            )
        )
        assert summary.document_id == document_id
        assert len(await attachments.list_by_question(question.id)) == 1

    async def test_plain_member_cannot_add_attachment_to_someone_elses_question(self) -> None:
        service, questions, _, communities, documents, _ = _seeded()
        question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientQuestionRoleError):
            await service.add_attachment(
                AddQuestionAttachmentInput(
                    question_id=question.id, acting_user_id=member_id, document_id=document_id
                )
            )

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _, documents, _ = _seeded()
        document_id = uuid4()
        documents.add_document(document_id)
        with pytest.raises(QuestionNotFoundError):
            await service.add_attachment(
                AddQuestionAttachmentInput(
                    question_id=uuid4(), acting_user_id=uuid4(), document_id=document_id
                )
            )

    async def test_unknown_document_raises(self) -> None:
        service, questions, _, communities, _, _ = _seeded()
        question = await _seed_question(questions, communities)

        with pytest.raises(DocumentNotFoundForQuestionError):
            await service.add_attachment(
                AddQuestionAttachmentInput(
                    question_id=question.id, acting_user_id=question.author_id, document_id=uuid4()
                )
            )

    async def test_duplicate_attachment_raises(self) -> None:
        service, questions, _, communities, documents, _ = _seeded()
        question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                document_id=document_id,
            )
        )

        with pytest.raises(DuplicateQuestionAttachmentError):
            await service.add_attachment(
                AddQuestionAttachmentInput(
                    question_id=question.id,
                    acting_user_id=question.author_id,
                    document_id=document_id,
                )
            )

    async def test_commits_and_publishes_event(self) -> None:
        service, questions, _, communities, documents, uow = _seeded()
        question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)

        await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                document_id=document_id,
            )
        )
        assert uow.committed is True
        assert any(isinstance(e, CommunityQuestionAttachmentAdded) for e in uow.published_events)

    async def test_the_same_document_can_be_attached_to_two_different_questions(self) -> None:
        service, questions, _, communities, documents, _ = _seeded()
        first_question = await _seed_question(questions, communities)
        second_question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)

        await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=first_question.id,
                acting_user_id=first_question.author_id,
                document_id=document_id,
            )
        )
        await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=second_question.id,
                acting_user_id=second_question.author_id,
                document_id=document_id,
            )
        )

        assert len(await service.list_attachments(first_question.id)) == 1
        assert len(await service.list_attachments(second_question.id)) == 1


class TestListAttachments:
    async def test_lists_added_attachments(self) -> None:
        service, questions, _, communities, documents, _ = _seeded()
        question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                document_id=document_id,
            )
        )

        result = await service.list_attachments(question.id)
        assert [a.document_id for a in result] == [document_id]


class TestRemoveAttachment:
    async def test_author_removes_an_attachment(self) -> None:
        service, questions, _, communities, documents, _ = _seeded()
        question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                document_id=document_id,
            )
        )

        await service.remove_attachment(
            RemoveQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                attachment_id=added.attachment_id,
            )
        )
        assert await service.list_attachments(question.id) == []

    async def test_moderator_removes_an_attachment_from_someone_elses_question(self) -> None:
        service, questions, _, communities, documents, _ = _seeded()
        question = await _seed_question(questions, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                document_id=document_id,
            )
        )
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=moderator_id,
                role=CommunityRole.MODERATOR,
            )
        )

        await service.remove_attachment(
            RemoveQuestionAttachmentInput(
                question_id=question.id,
                acting_user_id=moderator_id,
                attachment_id=added.attachment_id,
            )
        )
        assert await service.list_attachments(question.id) == []

    async def test_unknown_attachment_raises(self) -> None:
        service, questions, _, communities, _, _ = _seeded()
        question = await _seed_question(questions, communities)

        with pytest.raises(QuestionAttachmentNotFoundError):
            await service.remove_attachment(
                RemoveQuestionAttachmentInput(
                    question_id=question.id,
                    acting_user_id=question.author_id,
                    attachment_id=uuid4(),
                )
            )
