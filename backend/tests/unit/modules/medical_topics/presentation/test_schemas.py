"""Validation tests for the Medical Topics module's Pydantic v2 request
schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.presentation.schemas import (
    CreateTopicAliasRequest,
    CreateTopicRelationRequest,
    CreateTopicRequest,
    CreateTopicSpecialtyRequest,
    SetTopicFeaturedRequest,
    TopicAliasResponse,
    TopicFollowerResponse,
    TopicRelationResponse,
    TopicResponse,
    TopicSearchResponse,
    TopicSpecialtyResponse,
    UpdateTopicRequest,
)


class TestCreateTopicRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateTopicRequest(slug="cardiac-arrhythmia", name="Cardiac Arrhythmia")
        assert request.slug == "cardiac-arrhythmia"
        assert request.visibility is TopicVisibility.PUBLIC

    def test_slug_too_short_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest(slug="ab", name="Oncology")

    def test_slug_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest(slug="a" * 65, name="Oncology")

    @pytest.mark.parametrize(
        "slug", ["Oncology", "onco_logy", "onco logy", "-oncology", "oncology-"]
    )
    def test_slug_pattern_violations_are_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest(slug=slug, name="Oncology")

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest(slug="oncology", name="")

    def test_name_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest(slug="oncology", name="a" * 201)

    def test_description_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest(slug="oncology", name="Oncology", description="a" * 2001)

    def test_description_defaults_to_none(self) -> None:
        request = CreateTopicRequest(slug="oncology", name="Oncology")
        assert request.description is None

    def test_valid_color_is_accepted(self) -> None:
        request = CreateTopicRequest(slug="oncology", name="Oncology", color="#FF5733")
        assert request.color == "#FF5733"

    @pytest.mark.parametrize("color", ["FF5733", "#GG5733", "red", "#FF57"])
    def test_invalid_color_is_rejected(self, color: str) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest(slug="oncology", name="Oncology", color=color)

    def test_explicit_visibility_is_accepted(self) -> None:
        request = CreateTopicRequest(
            slug="oncology", name="Oncology", visibility=TopicVisibility.PRIVATE
        )
        assert request.visibility is TopicVisibility.PRIVATE

    def test_does_not_accept_server_controlled_fields(self) -> None:
        request = CreateTopicRequest.model_validate(
            {"slug": "oncology", "name": "Oncology", "id": "ignored", "created_by": "ignored"}
        )
        assert not hasattr(request, "id")
        assert not hasattr(request, "created_by")

    def test_rejects_unknown_visibility_value(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicRequest.model_validate(
                {"slug": "oncology", "name": "Oncology", "visibility": "not-a-real-value"}
            )


class TestUpdateTopicRequest:
    def test_all_fields_optional(self) -> None:
        request = UpdateTopicRequest()
        assert request.name is None
        assert request.description is None
        assert request.clear_description is False
        assert request.status is None
        assert request.visibility is None
        assert request.parent_id is None
        assert request.clear_parent is False
        assert request.specialty_id is None
        assert request.clear_specialty is False

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateTopicRequest(name="")

    def test_name_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateTopicRequest(name="a" * 201)

    def test_description_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateTopicRequest(description="a" * 2001)

    def test_valid_partial_update_is_accepted(self) -> None:
        request = UpdateTopicRequest(status=TopicStatus.PUBLISHED)
        assert request.status is TopicStatus.PUBLISHED

    def test_clear_description_flag_is_accepted(self) -> None:
        request = UpdateTopicRequest(clear_description=True)
        assert request.clear_description is True

    def test_invalid_color_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateTopicRequest(color="not-a-color")


class TestTopicResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        now = datetime.now(UTC)
        response = TopicResponse(
            id=uuid4(),
            slug="oncology",
            name="Oncology",
            status=TopicStatus.PUBLISHED,
            visibility=TopicVisibility.PUBLIC,
            created_at=now,
            updated_at=now,
        )
        assert response.slug == "oncology"
        assert response.description is None
        assert response.is_featured is False
        assert response.trending_score == 0.0

    def test_constructs_from_attributes(self) -> None:
        class _FakeSummary:
            id = uuid4()
            slug = "oncology"
            name = "Oncology"
            description = None
            icon = None
            color = None
            parent_id = None
            specialty_id = None
            status = TopicStatus.PUBLISHED
            visibility = TopicVisibility.PUBLIC
            is_featured = False
            trending_score = 0.0
            popularity_score = 0.0
            created_by = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        response = TopicResponse.model_validate(_FakeSummary())
        assert response.slug == "oncology"


class TestTopicSearchResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = TopicSearchResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0


class TestTopicFollowerResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = TopicFollowerResponse(
            id=uuid4(), topic_id=uuid4(), user_id=uuid4(), followed_at=datetime.now(UTC)
        )
        assert response.id is not None


class TestTopicSpecialtyResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = TopicSpecialtyResponse(
            id=uuid4(), name="Oncology", slug="oncology", is_active=True
        )
        assert response.name == "Oncology"
        assert response.description is None


class TestCreateTopicSpecialtyRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateTopicSpecialtyRequest(name="Oncology", slug="oncology")
        assert request.name == "Oncology"

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicSpecialtyRequest(name="", slug="oncology")

    def test_slug_too_short_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicSpecialtyRequest(name="Oncology", slug="ab")

    @pytest.mark.parametrize("slug", ["Oncology", "onco_logy", "onco logy"])
    def test_slug_pattern_violations_are_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            CreateTopicSpecialtyRequest(name="Oncology", slug=slug)


class TestTopicAliasResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = TopicAliasResponse(id=uuid4(), topic_id=uuid4(), alias="heart arrhythmia")
        assert response.alias == "heart arrhythmia"


class TestCreateTopicAliasRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateTopicAliasRequest(alias="heart arrhythmia")
        assert request.alias == "heart arrhythmia"

    def test_blank_alias_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicAliasRequest(alias="")

    def test_alias_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateTopicAliasRequest(alias="a" * 201)


class TestTopicRelationResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = TopicRelationResponse(
            id=uuid4(), topic_id=uuid4(), related_topic_id=uuid4(), relation_type="related"
        )
        assert response.relation_type == "related"


class TestCreateTopicRelationRequest:
    def test_defaults_relation_type_to_related(self) -> None:
        request = CreateTopicRelationRequest(related_topic_id=uuid4())
        assert request.relation_type == "related"

    def test_accepts_explicit_relation_type(self) -> None:
        request = CreateTopicRelationRequest(related_topic_id=uuid4(), relation_type="see_also")
        assert request.relation_type == "see_also"


class TestSetTopicFeaturedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetTopicFeaturedRequest(featured=True).featured is True

    def test_featured_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetTopicFeaturedRequest.model_validate({})
