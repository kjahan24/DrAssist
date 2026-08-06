"""Validation tests for the Community Posts module's Pydantic v2 request
schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.presentation.schemas import (
    AddPostAttachmentRequest,
    AssignPostTagRequest,
    AssignPostTopicRequest,
    CreatePostRequest,
    PostAttachmentResponse,
    PostFeedResponse,
    PostResponse,
    PostSearchResponse,
    PostTagResponse,
    PostTopicResponse,
    SetPostFeaturedRequest,
    SetPostLockedRequest,
    SetPostPinnedRequest,
    UpdatePostRequest,
)


class TestCreatePostRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreatePostRequest(title="A Clinical Case", body="Some detailed body text.")
        assert request.title == "A Clinical Case"
        assert request.post_type is PostType.DISCUSSION
        assert request.visibility is PostVisibility.PUBLIC
        assert request.is_anonymous is False
        assert request.topic_ids == []
        assert request.tags == []

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest(title="", body="Body text.")

    def test_title_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest(title="a" * 301, body="Body text.")

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest(title="Title", body="")

    def test_title_at_max_length_is_accepted(self) -> None:
        request = CreatePostRequest(title="a" * 300, body="Body text.")
        assert len(request.title) == 300

    def test_slug_at_min_length_is_accepted(self) -> None:
        request = CreatePostRequest(title="Title", body="Body text.", slug="abc")
        assert request.slug == "abc"

    def test_slug_at_max_length_is_accepted(self) -> None:
        slug = "a" * 100
        request = CreatePostRequest(title="Title", body="Body text.", slug=slug)
        assert request.slug == slug

    def test_slug_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest(title="Title", body="Body text.", slug="a" * 101)

    def test_excerpt_at_max_length_is_accepted(self) -> None:
        request = CreatePostRequest(title="Title", body="Body text.", excerpt="a" * 500)
        assert len(request.excerpt or "") == 500

    def test_accepts_every_post_type_value(self) -> None:
        for post_type in PostType:
            request = CreatePostRequest(title="Title", body="Body text.", post_type=post_type)
            assert request.post_type is post_type

    def test_accepts_every_visibility_value(self) -> None:
        for visibility in PostVisibility:
            request = CreatePostRequest(title="Title", body="Body text.", visibility=visibility)
            assert request.visibility is visibility

    def test_excerpt_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest(title="Title", body="Body text.", excerpt="a" * 501)

    def test_slug_too_short_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest(title="Title", body="Body text.", slug="ab")

    @pytest.mark.parametrize(
        "slug", ["Title-Case", "under_score", "has space", "-leading", "trailing-"]
    )
    def test_slug_pattern_violations_are_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest(title="Title", body="Body text.", slug=slug)

    def test_valid_slug_is_accepted(self) -> None:
        request = CreatePostRequest(title="Title", body="Body text.", slug="a-clinical-case")
        assert request.slug == "a-clinical-case"

    def test_explicit_post_type_is_accepted(self) -> None:
        request = CreatePostRequest(
            title="Title", body="Body text.", post_type=PostType.CLINICAL_CASE
        )
        assert request.post_type is PostType.CLINICAL_CASE

    def test_rejects_unknown_post_type_value(self) -> None:
        with pytest.raises(ValidationError):
            CreatePostRequest.model_validate(
                {"title": "Title", "body": "Body text.", "post_type": "not-a-real-type"}
            )

    def test_accepts_topic_ids_and_tags(self) -> None:
        topic_id = uuid4()
        request = CreatePostRequest(
            title="Title", body="Body text.", topic_ids=[topic_id], tags=["oncology"]
        )
        assert request.topic_ids == [topic_id]
        assert request.tags == ["oncology"]

    def test_does_not_accept_server_controlled_fields(self) -> None:
        request = CreatePostRequest.model_validate(
            {
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


class TestUpdatePostRequest:
    def test_all_fields_optional(self) -> None:
        request = UpdatePostRequest()
        assert request.title is None
        assert request.body is None
        assert request.excerpt is None
        assert request.regenerate_excerpt is False
        assert request.post_type is None
        assert request.visibility is None
        assert request.is_anonymous is None
        assert request.featured_image_document_id is None
        assert request.clear_featured_image is False

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdatePostRequest(title="")

    def test_blank_body_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdatePostRequest(body="")

    def test_excerpt_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdatePostRequest(excerpt="a" * 501)

    def test_valid_partial_update_is_accepted(self) -> None:
        request = UpdatePostRequest(visibility=PostVisibility.PRIVATE)
        assert request.visibility is PostVisibility.PRIVATE

    def test_regenerate_excerpt_flag_is_accepted(self) -> None:
        request = UpdatePostRequest(regenerate_excerpt=True)
        assert request.regenerate_excerpt is True

    def test_clear_featured_image_flag_is_accepted(self) -> None:
        request = UpdatePostRequest(clear_featured_image=True)
        assert request.clear_featured_image is True

    def test_title_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdatePostRequest(title="a" * 301)

    def test_accepts_a_featured_image_document_id(self) -> None:
        document_id = uuid4()
        request = UpdatePostRequest(featured_image_document_id=document_id)
        assert request.featured_image_document_id == document_id

    def test_accepts_every_post_type_value(self) -> None:
        for post_type in PostType:
            request = UpdatePostRequest(post_type=post_type)
            assert request.post_type is post_type


class TestSetPostPinnedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetPostPinnedRequest(pinned=True).pinned is True

    def test_pinned_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetPostPinnedRequest.model_validate({})


class TestSetPostLockedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetPostLockedRequest(locked=True).locked is True

    def test_locked_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetPostLockedRequest.model_validate({})


class TestSetPostFeaturedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetPostFeaturedRequest(featured=True).featured is True

    def test_featured_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetPostFeaturedRequest.model_validate({})


class TestPostResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        now = datetime.now(UTC)
        response = PostResponse(
            id=uuid4(),
            community_id=uuid4(),
            organization_id=uuid4(),
            author_id=uuid4(),
            slug="a-clinical-case",
            title="A Clinical Case",
            body="Body text.",
            excerpt="Excerpt.",
            post_type=PostType.DISCUSSION,
            status=PostStatus.DRAFT,
            visibility=PostVisibility.PUBLIC,
            is_anonymous=False,
            is_pinned=False,
            is_locked=False,
            is_featured=False,
            read_time_minutes=1,
            view_count=0,
            bookmark_count=0,
            share_count=0,
            created_at=now,
            updated_at=now,
        )
        assert response.slug == "a-clinical-case"
        assert response.featured_image_document_id is None
        assert response.published_at is None
        assert response.updated_by is None

    def test_constructs_from_attributes(self) -> None:
        class _FakeSummary:
            id = uuid4()
            community_id = uuid4()
            organization_id = uuid4()
            author_id = uuid4()
            slug = "a-clinical-case"
            title = "A Clinical Case"
            body = "Body text."
            excerpt = "Excerpt."
            post_type = PostType.DISCUSSION
            status = PostStatus.DRAFT
            visibility = PostVisibility.PUBLIC
            is_anonymous = False
            is_pinned = False
            is_locked = False
            is_featured = False
            read_time_minutes = 1
            view_count = 0
            bookmark_count = 0
            share_count = 0
            featured_image_document_id = None
            published_at = None
            updated_by = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        response = PostResponse.model_validate(_FakeSummary())
        assert response.slug == "a-clinical-case"


class TestPostSearchResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = PostSearchResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0


class TestPostFeedResponse:
    def test_defaults_next_cursor_to_none(self) -> None:
        response = PostFeedResponse(items=[])
        assert response.next_cursor is None

    def test_accepts_a_cursor(self) -> None:
        response = PostFeedResponse(items=[], next_cursor="abc123")
        assert response.next_cursor == "abc123"

    def test_total_is_required_on_search_response_but_absent_on_feed_response(self) -> None:
        with pytest.raises(ValidationError):
            PostSearchResponse.model_validate({"items": []})


class TestPostTopicResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = PostTopicResponse(id=uuid4(), post_id=uuid4(), topic_id=uuid4())
        assert response.id is not None


class TestAssignPostTopicRequest:
    def test_requires_topic_id(self) -> None:
        with pytest.raises(ValidationError):
            AssignPostTopicRequest.model_validate({})

    def test_accepts_a_topic_id(self) -> None:
        topic_id = uuid4()
        request = AssignPostTopicRequest(topic_id=topic_id)
        assert request.topic_id == topic_id


class TestPostTagResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = PostTagResponse(id=uuid4(), post_id=uuid4(), tag="oncology")
        assert response.tag == "oncology"


class TestAssignPostTagRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = AssignPostTagRequest(tag="oncology")
        assert request.tag == "oncology"

    def test_blank_tag_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssignPostTagRequest(tag="")

    def test_tag_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssignPostTagRequest(tag="a" * 51)


class TestPostAttachmentResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = PostAttachmentResponse(id=uuid4(), post_id=uuid4(), document_id=uuid4())
        assert response.id is not None


class TestAddPostAttachmentRequest:
    def test_requires_document_id(self) -> None:
        with pytest.raises(ValidationError):
            AddPostAttachmentRequest.model_validate({})

    def test_accepts_a_document_id(self) -> None:
        document_id = uuid4()
        request = AddPostAttachmentRequest(document_id=document_id)
        assert request.document_id == document_id
