"""Unit tests for `ManageAnswerAttachmentsService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community_answers.application.dto import (
    AddAnswerAttachmentInput,
    RemoveAnswerAttachmentInput,
)
from app.modules.community_answers.application.services.manage_answer_attachments_service import (
    ManageAnswerAttachmentsService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.exceptions import (
    AnswerAttachmentNotFoundError,
    AnswerNotFoundError,
    DocumentNotFoundForAnswerError,
    DuplicateAnswerAttachmentError,
    InsufficientAnswerRoleError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody
from tests.unit.modules.community_answers.application.fakes import (
    FakeCommunityAnswerAttachmentRepository,
    FakeCommunityAnswerRepository,
    FakeCommunityQueryPort,
    FakeDocumentQueryPort,
    FakeUnitOfWork,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManageAnswerAttachmentsService,
        FakeCommunityAnswerAttachmentRepository,
        FakeCommunityAnswerRepository,
        FakeCommunityQueryPort,
        FakeDocumentQueryPort,
        FakeUnitOfWork,
    ]
):
    attachments = FakeCommunityAnswerAttachmentRepository()
    answers = FakeCommunityAnswerRepository()
    communities = FakeCommunityQueryPort()
    documents = FakeDocumentQueryPort()
    uow = FakeUnitOfWork()
    service = ManageAnswerAttachmentsService(
        answer_attachment_repository=attachments,
        answer_repository=answers,
        community_query_port=communities,
        document_query_port=documents,
        unit_of_work=uow,
    )
    return service, attachments, answers, communities, documents, uow


async def _seed_answer(
    answers: FakeCommunityAnswerRepository, *, author_id: object, community_id: object
) -> CommunityAnswer:
    answer = CommunityAnswer.create(
        question_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=uuid4(),
        author_id=author_id,  # type: ignore[arg-type]
        body=AnswerBody("Body."),
    )
    await answers.add(answer)
    return answer


class TestAddAttachment:
    async def test_adds_an_attachment(self) -> None:
        service, attachments, answers, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)

        result = await service.add_attachment(
            AddAnswerAttachmentInput(
                answer_id=answer.id, acting_user_id=author_id, document_id=document_id
            )
        )
        assert result.document_id == document_id
        stored = await attachments.list_by_answer(answer.id)
        assert len(stored) == 1

    async def test_unknown_document_raises(self) -> None:
        service, _, answers, communities, _, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(DocumentNotFoundForAnswerError):
            await service.add_attachment(
                AddAnswerAttachmentInput(
                    answer_id=answer.id, acting_user_id=author_id, document_id=uuid4()
                )
            )

    async def test_duplicate_attachment_raises(self) -> None:
        service, _, answers, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)
        await service.add_attachment(
            AddAnswerAttachmentInput(
                answer_id=answer.id, acting_user_id=author_id, document_id=document_id
            )
        )

        with pytest.raises(DuplicateAnswerAttachmentError):
            await service.add_attachment(
                AddAnswerAttachmentInput(
                    answer_id=answer.id, acting_user_id=author_id, document_id=document_id
                )
            )

    async def test_plain_member_cannot_add_attachment_to_another_authors_answer(self) -> None:
        service, _, answers, communities, documents, _ = _seeded()
        author_id, other_id, community_id, document_id = uuid4(), uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))
        documents.add_document(document_id)

        with pytest.raises(InsufficientAnswerRoleError):
            await service.add_attachment(
                AddAnswerAttachmentInput(
                    answer_id=answer.id, acting_user_id=other_id, document_id=document_id
                )
            )

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.add_attachment(
                AddAnswerAttachmentInput(
                    answer_id=uuid4(), acting_user_id=uuid4(), document_id=uuid4()
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, answers, communities, documents, uow = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)

        await service.add_attachment(
            AddAnswerAttachmentInput(
                answer_id=answer.id, acting_user_id=author_id, document_id=document_id
            )
        )
        assert uow.committed is True


class TestListAttachments:
    async def test_lists_attachments_for_an_answer(self) -> None:
        service, _, answers, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)
        await service.add_attachment(
            AddAnswerAttachmentInput(
                answer_id=answer.id, acting_user_id=author_id, document_id=document_id
            )
        )

        result = await service.list_attachments(answer.id)
        assert len(result) == 1
        assert result[0].document_id == document_id

    async def test_returns_empty_list_for_an_answer_with_no_attachments(self) -> None:
        service, _, answers, communities, _, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)

        result = await service.list_attachments(answer.id)
        assert result == []


class TestRemoveAttachment:
    async def test_removes_an_attachment(self) -> None:
        service, attachments, answers, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddAnswerAttachmentInput(
                answer_id=answer.id, acting_user_id=author_id, document_id=document_id
            )
        )

        await service.remove_attachment(
            RemoveAnswerAttachmentInput(
                answer_id=answer.id, acting_user_id=author_id, attachment_id=added.attachment_id
            )
        )
        assert await attachments.list_by_answer(answer.id) == []

    async def test_unknown_attachment_raises(self) -> None:
        service, _, answers, communities, _, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(AnswerAttachmentNotFoundError):
            await service.remove_attachment(
                RemoveAnswerAttachmentInput(
                    answer_id=answer.id, acting_user_id=author_id, attachment_id=uuid4()
                )
            )

    async def test_plain_member_cannot_remove_attachment_from_another_authors_answer(self) -> None:
        service, _, answers, communities, documents, _ = _seeded()
        author_id, other_id, community_id, document_id = uuid4(), uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddAnswerAttachmentInput(
                answer_id=answer.id, acting_user_id=author_id, document_id=document_id
            )
        )

        with pytest.raises(InsufficientAnswerRoleError):
            await service.remove_attachment(
                RemoveAnswerAttachmentInput(
                    answer_id=answer.id, acting_user_id=other_id, attachment_id=added.attachment_id
                )
            )
