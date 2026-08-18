"""Unit tests for the Community Comments module's application-layer
DTOs — construction, defaults, the `.id` alias properties, and
`CommunityCommentSummaryDTO.author_id`'s optional (anonymous-maskable)
shape."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.community_comments.application.dto import (
    AddCommentAttachmentInput,
    ArchiveCommentInput,
    CommentAttachmentSummaryDTO,
    CommentFeedOutput,
    CommentRevisionSummaryDTO,
    CommunityCommentSummaryDTO,
    CreateCommentInput,
    CreateCommentOutput,
    CreateReplyInput,
    CreateReplyOutput,
    DeleteCommentInput,
    ListCommentsInput,
    ListRepliesInput,
    PublishCommentInput,
    RemoveCommentAttachmentInput,
    RestoreCommentInput,
    SearchCommentsInput,
    SearchCommentsOutput,
    ThreadOutput,
    UpdateCommentInput,
    UpdateCommentOutput,
)
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType


class TestCreateCommentDTOs:
    def test_create_comment_input_defaults(self) -> None:
        dto = CreateCommentInput(
            target_type=CommentTargetType.POST, target_id=uuid4(), author_id=uuid4(), body="Body"
        )
        assert dto.is_anonymous is False

    def test_create_comment_output(self) -> None:
        comment_id, target_id = uuid4(), uuid4()
        dto = CreateCommentOutput(
            comment_id=comment_id,
            target_type=CommentTargetType.QUESTION,
            target_id=target_id,
            status=CommentStatus.DRAFT,
        )
        assert dto.comment_id == comment_id
        assert dto.target_id == target_id
        assert dto.status is CommentStatus.DRAFT


class TestCreateReplyDTOs:
    def test_create_reply_input_defaults(self) -> None:
        dto = CreateReplyInput(parent_comment_id=uuid4(), author_id=uuid4(), body="Body")
        assert dto.is_anonymous is False

    def test_create_reply_output(self) -> None:
        comment_id, parent_id, root_id = uuid4(), uuid4(), uuid4()
        dto = CreateReplyOutput(
            comment_id=comment_id,
            parent_comment_id=parent_id,
            root_comment_id=root_id,
            depth=1,
            status=CommentStatus.DRAFT,
        )
        assert dto.comment_id == comment_id
        assert dto.parent_comment_id == parent_id
        assert dto.depth == 1


class TestUpdateCommentDTOs:
    def test_update_comment_input_defaults(self) -> None:
        dto = UpdateCommentInput(comment_id=uuid4(), acting_user_id=uuid4())
        assert dto.body is None

    def test_update_comment_output(self) -> None:
        dto = UpdateCommentOutput(
            comment_id=uuid4(), status=CommentStatus.PUBLISHED, revision_number=2
        )
        assert dto.status is CommentStatus.PUBLISHED
        assert dto.revision_number == 2


class TestSimpleActionInputs:
    def test_delete_comment_input(self) -> None:
        comment_id, user_id = uuid4(), uuid4()
        dto = DeleteCommentInput(comment_id=comment_id, acting_user_id=user_id)
        assert dto.comment_id == comment_id
        assert dto.acting_user_id == user_id

    def test_publish_comment_input(self) -> None:
        dto = PublishCommentInput(comment_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.comment_id, UUID)

    def test_archive_comment_input(self) -> None:
        dto = ArchiveCommentInput(comment_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.comment_id, UUID)

    def test_restore_comment_input(self) -> None:
        dto = RestoreCommentInput(comment_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.comment_id, UUID)


class TestCommunityCommentSummaryDTO:
    def _make(self, **overrides: object) -> CommunityCommentSummaryDTO:
        now = datetime.now(UTC)
        comment_id = uuid4()
        defaults: dict[str, object] = {
            "comment_id": comment_id,
            "target_type": CommentTargetType.POST,
            "target_id": uuid4(),
            "community_id": uuid4(),
            "organization_id": uuid4(),
            "body": "Body",
            "status": CommentStatus.DRAFT,
            "is_anonymous": False,
            "root_comment_id": comment_id,
            "depth": 0,
            "revision_number": 1,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return CommunityCommentSummaryDTO(**defaults)  # type: ignore[arg-type]

    def test_id_alias_matches_comment_id(self) -> None:
        dto = self._make()
        assert dto.id == dto.comment_id

    def test_optional_fields_default_to_none(self) -> None:
        dto = self._make()
        assert dto.topic_id is None
        assert dto.parent_comment_id is None
        assert dto.author_id is None
        assert dto.published_at is None
        assert dto.updated_by is None

    def test_is_immutable(self) -> None:
        dto = self._make()
        with pytest.raises(FrozenInstanceError):
            dto.body = "Changed"  # type: ignore[misc]

    def test_author_id_accepts_an_explicit_value(self) -> None:
        author_id = uuid4()
        dto = self._make(author_id=author_id, is_anonymous=False)
        assert dto.author_id == author_id

    def test_optional_fields_accept_explicit_values(self) -> None:
        updater_id, topic_id, parent_id = uuid4(), uuid4(), uuid4()
        now = datetime.now(UTC)
        dto = self._make(
            topic_id=topic_id, parent_comment_id=parent_id, published_at=now, updated_by=updater_id
        )
        assert dto.topic_id == topic_id
        assert dto.parent_comment_id == parent_id
        assert dto.published_at == now
        assert dto.updated_by == updater_id


class TestListAndSearchDTOs:
    def test_list_comments_input_defaults(self) -> None:
        org_id, target_id = uuid4(), uuid4()
        dto = ListCommentsInput(
            organization_id=org_id, target_type=CommentTargetType.POST, target_id=target_id
        )
        assert dto.status is None
        assert dto.sort_order == "desc"
        assert dto.cursor is None
        assert dto.limit == 20

    def test_list_comments_input_is_immutable(self) -> None:
        dto = ListCommentsInput(
            organization_id=uuid4(), target_type=CommentTargetType.POST, target_id=uuid4()
        )
        with pytest.raises(FrozenInstanceError):
            dto.limit = 99  # type: ignore[misc]

    def test_list_replies_input_defaults(self) -> None:
        org_id, parent_id = uuid4(), uuid4()
        dto = ListRepliesInput(organization_id=org_id, parent_comment_id=parent_id)
        assert dto.parent_comment_id == parent_id
        assert dto.limit == 20

    def test_comment_feed_output_defaults(self) -> None:
        dto = CommentFeedOutput(items=())
        assert dto.next_cursor is None

    def test_search_comments_input_query_is_optional(self) -> None:
        org_id = uuid4()
        dto = SearchCommentsInput(organization_id=org_id)
        assert dto.query is None
        assert dto.top_level_only is False
        assert dto.include_deleted is False
        assert not hasattr(dto, "offset")

    def test_search_comments_input_accepts_all_filters(self) -> None:
        org_id, target_id, community_id, topic_id, author_id, parent_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        now = datetime.now(UTC)
        dto = SearchCommentsInput(
            organization_id=org_id,
            query="term",
            target_type=CommentTargetType.ANSWER,
            target_id=target_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            parent_comment_id=parent_id,
            top_level_only=True,
            status=(CommentStatus.PUBLISHED,),
            created_from=now,
            created_to=now,
            include_deleted=True,
            sort_order="asc",
            cursor="abc",
            limit=5,
        )
        assert dto.target_id == target_id
        assert dto.community_id == community_id
        assert dto.topic_id == topic_id
        assert dto.author_id == author_id
        assert dto.parent_comment_id == parent_id
        assert dto.top_level_only is True
        assert dto.include_deleted is True
        assert dto.sort_order == "asc"
        assert dto.limit == 5

    def test_search_comments_input_is_immutable(self) -> None:
        dto = SearchCommentsInput(organization_id=uuid4())
        with pytest.raises(FrozenInstanceError):
            dto.query = "changed"  # type: ignore[misc]

    def test_search_comments_output(self) -> None:
        dto = SearchCommentsOutput(items=())
        assert dto.next_cursor is None

    def test_thread_output(self) -> None:
        dto = ThreadOutput(items=())
        assert dto.items == ()


class TestCommentRevisionDTO:
    def test_id_alias_matches_revision_id(self) -> None:
        revision_id = uuid4()
        dto = CommentRevisionSummaryDTO(
            revision_id=revision_id,
            comment_id=uuid4(),
            revision_number=1,
            previous_body="Old body.",
            author_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert dto.id == revision_id


class TestCommentAttachmentDTOs:
    def test_id_alias_matches_attachment_id(self) -> None:
        attachment_id = uuid4()
        dto = CommentAttachmentSummaryDTO(
            attachment_id=attachment_id, comment_id=uuid4(), document_id=uuid4()
        )
        assert dto.id == attachment_id

    def test_add_comment_attachment_input(self) -> None:
        document_id = uuid4()
        dto = AddCommentAttachmentInput(
            comment_id=uuid4(), acting_user_id=uuid4(), document_id=document_id
        )
        assert dto.document_id == document_id

    def test_remove_comment_attachment_input(self) -> None:
        dto = RemoveCommentAttachmentInput(
            comment_id=uuid4(), acting_user_id=uuid4(), attachment_id=uuid4()
        )
        assert isinstance(dto.attachment_id, UUID)
