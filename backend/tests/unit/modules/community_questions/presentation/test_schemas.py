"""Validation tests for the Community Questions module's Pydantic v2
request schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.presentation.schemas import (
    AddQuestionAttachmentRequest,
    AssignQuestionTagRequest,
    AssignQuestionTopicRequest,
    CreateQuestionRequest,
    QuestionAttachmentResponse,
    QuestionFeedResponse,
    QuestionFollowerResponse,
    QuestionResponse,
    QuestionSearchResponse,
    QuestionTagResponse,
    QuestionTopicResponse,
    SetQuestionFeaturedRequest,
    SetQuestionPinnedRequest,
    UpdateQuestionRequest,
)


class TestCreateQuestionRequest:
    def test_valid_request_is_accepted(self) -> None:
        primary_topic_id = uuid4()
        request = CreateQuestionRequest(
            primary_topic_id=primary_topic_id,
            title="How should hypertension be managed?",
            body="Some detailed body text.",
        )
        assert request.primary_topic_id == primary_topic_id
        assert request.question_type is QuestionType.GENERAL
        assert request.visibility is QuestionVisibility.PUBLIC
        assert request.is_anonymous is False
        assert request.secondary_topic_ids == []
        assert request.tags == []

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateQuestionRequest(primary_topic_id=uuid4(), title="", body="Body text.")

    def test_title_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateQuestionRequest(primary_topic_id=uuid4(), title="a" * 301, body="Body text.")

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateQuestionRequest(primary_topic_id=uuid4(), title="Title", body="")

    def test_primary_topic_id_is_required(self) -> None:
        with pytest.raises(ValidationError):
            CreateQuestionRequest.model_validate({"title": "Title", "body": "Body text."})

    def test_title_at_max_length_is_accepted(self) -> None:
        request = CreateQuestionRequest(
            primary_topic_id=uuid4(), title="a" * 300, body="Body text."
        )
        assert len(request.title) == 300

    def test_slug_at_min_length_is_accepted(self) -> None:
        request = CreateQuestionRequest(
            primary_topic_id=uuid4(), title="Title", body="Body text.", slug="abc"
        )
        assert request.slug == "abc"

    def test_slug_at_max_length_is_accepted(self) -> None:
        slug = "a" * 100
        request = CreateQuestionRequest(
            primary_topic_id=uuid4(), title="Title", body="Body text.", slug=slug
        )
        assert request.slug == slug

    def test_slug_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateQuestionRequest(
                primary_topic_id=uuid4(), title="Title", body="Body text.", slug="a" * 101
            )

    @pytest.mark.parametrize(
        "slug", ["Title-Case", "under_score", "has space", "-leading", "trailing-"]
    )
    def test_slug_pattern_violations_are_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            CreateQuestionRequest(
                primary_topic_id=uuid4(), title="Title", body="Body text.", slug=slug
            )

    def test_summary_at_max_length_is_accepted(self) -> None:
        request = CreateQuestionRequest(
            primary_topic_id=uuid4(), title="Title", body="Body text.", summary="a" * 500
        )
        assert len(request.summary or "") == 500

    def test_accepts_every_question_type_value(self) -> None:
        for question_type in QuestionType:
            request = CreateQuestionRequest(
                primary_topic_id=uuid4(),
                title="Title",
                body="Body text.",
                question_type=question_type,
            )
            assert request.question_type is question_type

    def test_accepts_every_visibility_value(self) -> None:
        for visibility in QuestionVisibility:
            request = CreateQuestionRequest(
                primary_topic_id=uuid4(), title="Title", body="Body text.", visibility=visibility
            )
            assert request.visibility is visibility

    def test_accepts_secondary_topic_ids_and_tags(self) -> None:
        secondary_topic_id = uuid4()
        request = CreateQuestionRequest(
            primary_topic_id=uuid4(),
            title="Title",
            body="Body text.",
            secondary_topic_ids=[secondary_topic_id],
            tags=["oncology"],
        )
        assert request.secondary_topic_ids == [secondary_topic_id]
        assert request.tags == ["oncology"]

    def test_does_not_accept_server_controlled_fields(self) -> None:
        request = CreateQuestionRequest.model_validate(
            {
                "primary_topic_id": str(uuid4()),
                "title": "Title",
                "body": "Body text.",
                "id": "ignored",
                "author_id": "ignored",
                "status": "ignored",
            }
        )
        assert not hasattr(request, "id")
        assert not hasattr(request, "author_id")
        assert not hasattr(request, "status")


class TestUpdateQuestionRequest:
    def test_all_fields_optional(self) -> None:
        request = UpdateQuestionRequest()
        assert request.title is None
        assert request.body is None
        assert request.summary is None
        assert request.regenerate_summary is False
        assert request.question_type is None
        assert request.visibility is None
        assert request.is_anonymous is None

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateQuestionRequest(title="")

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateQuestionRequest(body="")

    def test_title_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateQuestionRequest(title="a" * 301)

    def test_summary_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateQuestionRequest(summary="a" * 501)

    def test_valid_partial_update_is_accepted(self) -> None:
        request = UpdateQuestionRequest(visibility=QuestionVisibility.PRIVATE)
        assert request.visibility is QuestionVisibility.PRIVATE

    def test_regenerate_summary_flag_is_accepted(self) -> None:
        request = UpdateQuestionRequest(regenerate_summary=True)
        assert request.regenerate_summary is True

    def test_accepts_every_question_type_value(self) -> None:
        for question_type in QuestionType:
            request = UpdateQuestionRequest(question_type=question_type)
            assert request.question_type is question_type


class TestSetQuestionPinnedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetQuestionPinnedRequest(pinned=True).pinned is True

    def test_pinned_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetQuestionPinnedRequest.model_validate({})


class TestSetQuestionFeaturedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetQuestionFeaturedRequest(featured=True).featured is True

    def test_featured_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetQuestionFeaturedRequest.model_validate({})


class TestQuestionResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        now = datetime.now(UTC)
        response = QuestionResponse(
            id=uuid4(),
            community_id=uuid4(),
            organization_id=uuid4(),
            author_id=uuid4(),
            primary_topic_id=uuid4(),
            slug="how-to-manage-hypertension",
            title="How should hypertension be managed?",
            body="Body text.",
            summary="Summary.",
            question_type=QuestionType.GENERAL,
            status=QuestionStatus.DRAFT,
            visibility=QuestionVisibility.PUBLIC,
            is_anonymous=False,
            is_pinned=False,
            is_featured=False,
            read_time_minutes=1,
            view_count=0,
            follower_count=0,
            bookmark_count=0,
            share_count=0,
            created_at=now,
            updated_at=now,
        )
        assert response.slug == "how-to-manage-hypertension"
        assert response.accepted_answer_id is None
        assert response.published_at is None
        assert response.updated_by is None

    def test_constructs_from_attributes(self) -> None:
        class _FakeSummary:
            id = uuid4()
            community_id = uuid4()
            organization_id = uuid4()
            author_id = uuid4()
            primary_topic_id = uuid4()
            slug = "title"
            title = "Title"
            body = "Body text."
            summary = "Summary."
            question_type = QuestionType.GENERAL
            status = QuestionStatus.DRAFT
            visibility = QuestionVisibility.PUBLIC
            is_anonymous = False
            is_pinned = False
            is_featured = False
            read_time_minutes = 1
            view_count = 0
            follower_count = 0
            bookmark_count = 0
            share_count = 0
            accepted_answer_id = None
            published_at = None
            updated_by = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        response = QuestionResponse.model_validate(_FakeSummary())
        assert response.slug == "title"


class TestQuestionSearchResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = QuestionSearchResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0


class TestQuestionFeedResponse:
    def test_defaults_next_cursor_to_none(self) -> None:
        response = QuestionFeedResponse(items=[])
        assert response.next_cursor is None

    def test_accepts_a_cursor(self) -> None:
        response = QuestionFeedResponse(items=[], next_cursor="abc123")
        assert response.next_cursor == "abc123"


class TestQuestionTopicResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = QuestionTopicResponse(id=uuid4(), question_id=uuid4(), topic_id=uuid4())
        assert response.id is not None


class TestAssignQuestionTopicRequest:
    def test_requires_topic_id(self) -> None:
        with pytest.raises(ValidationError):
            AssignQuestionTopicRequest.model_validate({})

    def test_accepts_a_topic_id(self) -> None:
        topic_id = uuid4()
        request = AssignQuestionTopicRequest(topic_id=topic_id)
        assert request.topic_id == topic_id


class TestQuestionTagResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = QuestionTagResponse(id=uuid4(), question_id=uuid4(), tag="oncology")
        assert response.tag == "oncology"


class TestAssignQuestionTagRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = AssignQuestionTagRequest(tag="oncology")
        assert request.tag == "oncology"

    def test_blank_tag_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssignQuestionTagRequest(tag="")

    def test_tag_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssignQuestionTagRequest(tag="a" * 51)


class TestQuestionAttachmentResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = QuestionAttachmentResponse(id=uuid4(), question_id=uuid4(), document_id=uuid4())
        assert response.id is not None


class TestAddQuestionAttachmentRequest:
    def test_requires_document_id(self) -> None:
        with pytest.raises(ValidationError):
            AddQuestionAttachmentRequest.model_validate({})

    def test_accepts_a_document_id(self) -> None:
        document_id = uuid4()
        request = AddQuestionAttachmentRequest(document_id=document_id)
        assert request.document_id == document_id


class TestQuestionFollowerResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = QuestionFollowerResponse(id=uuid4(), question_id=uuid4(), user_id=uuid4())
        assert response.id is not None
