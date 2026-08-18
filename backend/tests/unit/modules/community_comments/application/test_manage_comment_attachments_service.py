"""Unit tests for `ManageCommentAttachmentsService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community_comments.application.dto import (
    AddCommentAttachmentInput,
    RemoveCommentAttachmentInput,
)
from app.modules.community_comments.application.services.manage_comment_attachments_service import (
    ManageCommentAttachmentsService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.exceptions import (
    CommentAttachmentNotFoundError,
    CommentNotFoundError,
    DocumentNotFoundForCommentError,
    DuplicateCommentAttachmentError,
    InsufficientCommentRoleError,
)
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import (
    FakeCommunityCommentAttachmentRepository,
    FakeCommunityCommentRepository,
    FakeCommunityQueryPort,
    FakeDocumentQueryPort,
    FakeUnitOfWork,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManageCommentAttachmentsService,
        FakeCommunityCommentAttachmentRepository,
        FakeCommunityCommentRepository,
        FakeCommunityQueryPort,
        FakeDocumentQueryPort,
        FakeUnitOfWork,
    ]
):
    attachments = FakeCommunityCommentAttachmentRepository()
    comments = FakeCommunityCommentRepository()
    communities = FakeCommunityQueryPort()
    documents = FakeDocumentQueryPort()
    uow = FakeUnitOfWork()
    service = ManageCommentAttachmentsService(
        comment_attachment_repository=attachments,
        comment_repository=comments,
        community_query_port=communities,
        document_query_port=documents,
        unit_of_work=uow,
    )
    return service, attachments, comments, communities, documents, uow


async def _seed_comment(
    comments: FakeCommunityCommentRepository, *, author_id: object, community_id: object
) -> CommunityComment:
    comment = CommunityComment.create(
        target_type=CommentTargetType.POST,
        target_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=None,
        author_id=author_id,  # type: ignore[arg-type]
        body=CommentBody("Body."),
    )
    await comments.add(comment)
    return comment


class TestAddAttachment:
    async def test_adds_an_attachment(self) -> None:
        service, attachments, comments, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)

        result = await service.add_attachment(
            AddCommentAttachmentInput(
                comment_id=comment.id, acting_user_id=author_id, document_id=document_id
            )
        )
        assert result.document_id == document_id
        assert len(await attachments.list_by_comment(comment.id)) == 1

    async def test_unknown_document_raises(self) -> None:
        service, _, comments, communities, _, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(DocumentNotFoundForCommentError):
            await service.add_attachment(
                AddCommentAttachmentInput(
                    comment_id=comment.id, acting_user_id=author_id, document_id=uuid4()
                )
            )

    async def test_duplicate_attachment_raises(self) -> None:
        service, _, comments, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)
        await service.add_attachment(
            AddCommentAttachmentInput(
                comment_id=comment.id, acting_user_id=author_id, document_id=document_id
            )
        )

        with pytest.raises(DuplicateCommentAttachmentError):
            await service.add_attachment(
                AddCommentAttachmentInput(
                    comment_id=comment.id, acting_user_id=author_id, document_id=document_id
                )
            )

    async def test_plain_member_cannot_add_attachment_to_another_authors_comment(self) -> None:
        service, _, comments, communities, documents, _ = _seeded()
        author_id, other_id, community_id, document_id = uuid4(), uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))
        documents.add_document(document_id)

        with pytest.raises(InsufficientCommentRoleError):
            await service.add_attachment(
                AddCommentAttachmentInput(
                    comment_id=comment.id, acting_user_id=other_id, document_id=document_id
                )
            )

    async def test_unknown_comment_raises(self) -> None:
        service, _, _, _, _, _ = _seeded()
        with pytest.raises(CommentNotFoundError):
            await service.add_attachment(
                AddCommentAttachmentInput(
                    comment_id=uuid4(), acting_user_id=uuid4(), document_id=uuid4()
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, comments, communities, documents, uow = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)

        await service.add_attachment(
            AddCommentAttachmentInput(
                comment_id=comment.id, acting_user_id=author_id, document_id=document_id
            )
        )
        assert uow.committed is True


class TestListAttachments:
    async def test_lists_attachments_for_a_comment(self) -> None:
        service, _, comments, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)
        await service.add_attachment(
            AddCommentAttachmentInput(
                comment_id=comment.id, acting_user_id=author_id, document_id=document_id
            )
        )

        result = await service.list_attachments(comment.id)
        assert len(result) == 1
        assert result[0].document_id == document_id

    async def test_returns_empty_list_for_a_comment_with_no_attachments(self) -> None:
        service, _, comments, communities, _, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)

        result = await service.list_attachments(comment.id)
        assert result == []


class TestRemoveAttachment:
    async def test_removes_an_attachment(self) -> None:
        service, attachments, comments, communities, documents, _ = _seeded()
        author_id, community_id, document_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddCommentAttachmentInput(
                comment_id=comment.id, acting_user_id=author_id, document_id=document_id
            )
        )

        await service.remove_attachment(
            RemoveCommentAttachmentInput(
                comment_id=comment.id, acting_user_id=author_id, attachment_id=added.attachment_id
            )
        )
        assert await attachments.list_by_comment(comment.id) == []

    async def test_unknown_attachment_raises(self) -> None:
        service, _, comments, communities, _, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(CommentAttachmentNotFoundError):
            await service.remove_attachment(
                RemoveCommentAttachmentInput(
                    comment_id=comment.id, acting_user_id=author_id, attachment_id=uuid4()
                )
            )

    async def test_plain_member_cannot_remove_attachment_from_another_authors_comment(self) -> None:
        service, _, comments, communities, documents, _ = _seeded()
        author_id, other_id, community_id, document_id = uuid4(), uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddCommentAttachmentInput(
                comment_id=comment.id, acting_user_id=author_id, document_id=document_id
            )
        )

        with pytest.raises(InsufficientCommentRoleError):
            await service.remove_attachment(
                RemoveCommentAttachmentInput(
                    comment_id=comment.id,
                    acting_user_id=other_id,
                    attachment_id=added.attachment_id,
                )
            )
