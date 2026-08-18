"""Validation tests for the Community Answers module's Pydantic v2
request/response schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.presentation.schemas import (
    AddAnswerAttachmentRequest,
    AnswerAttachmentResponse,
    AnswerFeedResponse,
    AnswerResponse,
    AnswerRevisionResponse,
    AnswerSearchResponse,
    CreateAnswerRequest,
    SetAnswerFeaturedRequest,
    SetAnswerPinnedRequest,
    UpdateAnswerRequest,
)


class TestCreateAnswerRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateAnswerRequest(body="A detailed answer body.")
        assert request.body == "A detailed answer body."
        assert request.summary is None
        assert request.visibility is AnswerVisibility.PUBLIC
        assert request.is_anonymous is False

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateAnswerRequest(body="")

    def test_body_is_required(self) -> None:
        with pytest.raises(ValidationError):
            CreateAnswerRequest.model_validate({})

    def test_summary_at_max_length_is_accepted(self) -> None:
        request = CreateAnswerRequest(body="Body.", summary="a" * 500)
        assert len(request.summary or "") == 500

    def test_summary_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateAnswerRequest(body="Body.", summary="a" * 501)

    def test_accepts_every_visibility_value(self) -> None:
        for visibility in AnswerVisibility:
            request = CreateAnswerRequest(body="Body.", visibility=visibility)
            assert request.visibility is visibility

    def test_accepts_is_anonymous(self) -> None:
        request = CreateAnswerRequest(body="Body.", is_anonymous=True)
        assert request.is_anonymous is True

    def test_does_not_accept_server_controlled_fields(self) -> None:
        request = CreateAnswerRequest.model_validate(
            {
                "body": "Body.",
                "id": "ignored",
                "author_id": "ignored",
                "status": "ignored",
                "question_id": "ignored",
            }
        )
        assert not hasattr(request, "id")
        assert not hasattr(request, "author_id")
        assert not hasattr(request, "status")
        assert not hasattr(request, "question_id")

    def test_invalid_visibility_value_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateAnswerRequest.model_validate({"body": "Body.", "visibility": "not-a-real-tier"})


class TestUpdateAnswerRequest:
    def test_all_fields_optional(self) -> None:
        request = UpdateAnswerRequest()
        assert request.body is None
        assert request.summary is None
        assert request.regenerate_summary is False

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateAnswerRequest(body="")

    def test_summary_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateAnswerRequest(summary="a" * 501)

    def test_valid_partial_update_is_accepted(self) -> None:
        request = UpdateAnswerRequest(body="New body.")
        assert request.body == "New body."

    def test_regenerate_summary_flag_is_accepted(self) -> None:
        request = UpdateAnswerRequest(regenerate_summary=True)
        assert request.regenerate_summary is True

    def test_does_not_accept_server_controlled_fields(self) -> None:
        request = UpdateAnswerRequest.model_validate(
            {"body": "New body.", "id": "ignored", "status": "ignored"}
        )
        assert not hasattr(request, "id")
        assert not hasattr(request, "status")


class TestSetAnswerFeaturedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetAnswerFeaturedRequest(featured=True).featured is True

    def test_featured_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetAnswerFeaturedRequest.model_validate({})


class TestSetAnswerPinnedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetAnswerPinnedRequest(pinned=True).pinned is True

    def test_pinned_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetAnswerPinnedRequest.model_validate({})


class TestAnswerResponse:
    def _full_field_set(self, **overrides: object) -> dict[str, object]:
        now = datetime.now(UTC)
        defaults: dict[str, object] = {
            "id": uuid4(),
            "question_id": uuid4(),
            "community_id": uuid4(),
            "organization_id": uuid4(),
            "topic_id": uuid4(),
            "body": "Body text.",
            "summary": "Summary.",
            "status": AnswerStatus.DRAFT,
            "visibility": AnswerVisibility.PUBLIC,
            "is_anonymous": False,
            "is_best_answer": False,
            "is_featured": False,
            "is_pinned": False,
            "view_count": 0,
            "share_count": 0,
            "revision_number": 1,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return defaults

    def test_constructs_from_a_full_field_set(self) -> None:
        response = AnswerResponse(**self._full_field_set())
        assert response.author_id is None
        assert response.published_at is None
        assert response.updated_by is None

    def test_accepts_an_explicit_author_id(self) -> None:
        author_id = uuid4()
        response = AnswerResponse(**self._full_field_set(author_id=author_id))
        assert response.author_id == author_id

    def test_invalid_status_value_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AnswerResponse.model_validate(self._full_field_set(status="not-a-real-status"))

    def test_invalid_visibility_value_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AnswerResponse.model_validate(self._full_field_set(visibility="not-a-real-tier"))

    def test_accepts_every_status_value(self) -> None:
        for status in AnswerStatus:
            response = AnswerResponse.model_validate(self._full_field_set(status=status))
            assert response.status is status

    def test_accepts_every_visibility_value(self) -> None:
        for visibility in AnswerVisibility:
            response = AnswerResponse.model_validate(self._full_field_set(visibility=visibility))
            assert response.visibility is visibility

    def test_constructs_from_attributes(self) -> None:
        class _FakeSummary:
            id = uuid4()
            question_id = uuid4()
            community_id = uuid4()
            organization_id = uuid4()
            topic_id = uuid4()
            body = "Body text."
            summary = "Summary."
            status = AnswerStatus.DRAFT
            visibility = AnswerVisibility.PUBLIC
            is_anonymous = False
            is_best_answer = False
            is_featured = False
            is_pinned = False
            view_count = 0
            share_count = 0
            revision_number = 1
            author_id = None
            published_at = None
            updated_by = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        response = AnswerResponse.model_validate(_FakeSummary())
        assert response.status is AnswerStatus.DRAFT


class TestAnswerSearchResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = AnswerSearchResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0


class TestAnswerFeedResponse:
    def test_defaults_next_cursor_to_none(self) -> None:
        response = AnswerFeedResponse(items=[])
        assert response.next_cursor is None

    def test_accepts_a_cursor(self) -> None:
        response = AnswerFeedResponse(items=[], next_cursor="abc123")
        assert response.next_cursor == "abc123"


class TestAnswerRevisionResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = AnswerRevisionResponse(
            id=uuid4(),
            answer_id=uuid4(),
            revision_number=1,
            previous_body="Old body.",
            author_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert response.revision_number == 1


class TestAnswerAttachmentResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = AnswerAttachmentResponse(id=uuid4(), answer_id=uuid4(), document_id=uuid4())
        assert response.id is not None


class TestAddAnswerAttachmentRequest:
    def test_requires_document_id(self) -> None:
        with pytest.raises(ValidationError):
            AddAnswerAttachmentRequest.model_validate({})

    def test_accepts_a_document_id(self) -> None:
        document_id = uuid4()
        request = AddAnswerAttachmentRequest(document_id=document_id)
        assert request.document_id == document_id
