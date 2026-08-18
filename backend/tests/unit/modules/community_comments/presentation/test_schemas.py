"""Validation tests for the Community Comments module's Pydantic v2
request/response schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.presentation.schemas import (
    AddCommentAttachmentRequest,
    CommentAttachmentResponse,
    CommentFeedResponse,
    CommentResponse,
    CommentRevisionResponse,
    CommentSearchResponse,
    CreateCommentRequest,
    CreateReplyRequest,
    ThreadResponse,
    UpdateCommentRequest,
)


class TestCreateCommentRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateCommentRequest(body="A comment body.")
        assert request.body == "A comment body."
        assert request.is_anonymous is False

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommentRequest(body="")

    def test_body_is_required(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommentRequest.model_validate({})

    def test_accepts_is_anonymous(self) -> None:
        request = CreateCommentRequest(body="Body.", is_anonymous=True)
        assert request.is_anonymous is True

    def test_does_not_accept_server_controlled_fields(self) -> None:
        request = CreateCommentRequest.model_validate(
            {
                "body": "Body.",
                "id": "ignored",
                "author_id": "ignored",
                "status": "ignored",
                "target_type": "ignored",
                "target_id": "ignored",
            }
        )
        assert not hasattr(request, "id")
        assert not hasattr(request, "author_id")
        assert not hasattr(request, "status")
        assert not hasattr(request, "target_type")
        assert not hasattr(request, "target_id")


class TestCreateReplyRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateReplyRequest(body="A reply body.")
        assert request.body == "A reply body."
        assert request.is_anonymous is False

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateReplyRequest(body="")

    def test_does_not_accept_a_parent_comment_id_field(self) -> None:
        request = CreateReplyRequest.model_validate(
            {"body": "Body.", "parent_comment_id": "ignored"}
        )
        assert not hasattr(request, "parent_comment_id")


class TestUpdateCommentRequest:
    def test_body_is_optional(self) -> None:
        request = UpdateCommentRequest()
        assert request.body is None

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCommentRequest(body="")

    def test_valid_body_is_accepted(self) -> None:
        request = UpdateCommentRequest(body="New body.")
        assert request.body == "New body."


class TestCommentResponse:
    def _full_field_set(self, **overrides: object) -> dict[str, object]:
        now = datetime.now(UTC)
        comment_id = uuid4()
        defaults: dict[str, object] = {
            "id": comment_id,
            "target_type": CommentTargetType.POST,
            "target_id": uuid4(),
            "community_id": uuid4(),
            "organization_id": uuid4(),
            "body": "Body text.",
            "status": CommentStatus.DRAFT,
            "is_anonymous": False,
            "root_comment_id": comment_id,
            "depth": 0,
            "revision_number": 1,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return defaults

    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommentResponse(**self._full_field_set())
        assert response.author_id is None
        assert response.topic_id is None
        assert response.parent_comment_id is None
        assert response.published_at is None
        assert response.updated_by is None

    def test_accepts_an_explicit_author_id(self) -> None:
        author_id = uuid4()
        response = CommentResponse(**self._full_field_set(author_id=author_id))
        assert response.author_id == author_id

    def test_constructs_from_attributes(self) -> None:
        class _FakeSummary:
            id = uuid4()
            target_type = CommentTargetType.QUESTION
            target_id = uuid4()
            community_id = uuid4()
            organization_id = uuid4()
            body = "Body text."
            status = CommentStatus.DRAFT
            is_anonymous = False
            root_comment_id = id
            depth = 0
            revision_number = 1
            topic_id = None
            parent_comment_id = None
            author_id = None
            published_at = None
            updated_by = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        response = CommentResponse.model_validate(_FakeSummary())
        assert response.status is CommentStatus.DRAFT


class TestCommentFeedResponse:
    def test_defaults_next_cursor_to_none(self) -> None:
        response = CommentFeedResponse(items=[])
        assert response.next_cursor is None

    def test_accepts_a_cursor(self) -> None:
        response = CommentFeedResponse(items=[], next_cursor="abc123")
        assert response.next_cursor == "abc123"


class TestCommentSearchResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = CommentSearchResponse(items=[], next_cursor=None)
        assert response.items == []
        assert response.next_cursor is None


class TestThreadResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = ThreadResponse(items=[])
        assert response.items == []


class TestCommentRevisionResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommentRevisionResponse(
            id=uuid4(),
            comment_id=uuid4(),
            revision_number=1,
            previous_body="Old body.",
            author_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert response.revision_number == 1


class TestCommentAttachmentResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommentAttachmentResponse(id=uuid4(), comment_id=uuid4(), document_id=uuid4())
        assert response.id is not None


class TestAddCommentAttachmentRequest:
    def test_requires_document_id(self) -> None:
        with pytest.raises(ValidationError):
            AddCommentAttachmentRequest.model_validate({})

    def test_accepts_a_document_id(self) -> None:
        document_id = uuid4()
        request = AddCommentAttachmentRequest(document_id=document_id)
        assert request.document_id == document_id
