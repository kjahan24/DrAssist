"""Validation tests for the Community module's Pydantic v2 request
schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.presentation.schemas import (
    AssignCommunityTagRequest,
    CommunityCategoryResponse,
    CommunityMemberResponse,
    CommunityResponse,
    CommunityRuleResponse,
    CommunitySearchResponse,
    CommunityStatisticsResponse,
    CommunityTagResponse,
    CommunityTagSearchResponse,
    CreateCommunityCategoryRequest,
    CreateCommunityRequest,
    CreateCommunityRuleRequest,
    ReorderCommunityRulesRequest,
    SetCommunityFeaturedRequest,
    SetCommunityRuleEnabledRequest,
    SetCommunityVerifiedRequest,
    UpdateCommunityRequest,
    UpdateCommunityRuleRequest,
)


class TestCreateCommunityRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateCommunityRequest(slug="oncology-support", name="Oncology Support")
        assert request.slug == "oncology-support"
        assert request.visibility is CommunityVisibility.PUBLIC

    def test_slug_too_short_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRequest(slug="ab", name="Oncology")

    def test_slug_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRequest(slug="a" * 65, name="Oncology")

    @pytest.mark.parametrize(
        "slug", ["Oncology", "onco_support", "onco support", "-oncology", "oncology-"]
    )
    def test_slug_pattern_violations_are_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRequest(slug=slug, name="Oncology")

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRequest(slug="oncology", name="")

    def test_name_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRequest(slug="oncology", name="a" * 201)

    def test_description_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRequest(slug="oncology", name="Oncology", description="a" * 2001)

    def test_description_defaults_to_none(self) -> None:
        request = CreateCommunityRequest(slug="oncology", name="Oncology")
        assert request.description is None

    def test_explicit_visibility_is_accepted(self) -> None:
        request = CreateCommunityRequest(
            slug="oncology", name="Oncology", visibility=CommunityVisibility.PRIVATE
        )
        assert request.visibility is CommunityVisibility.PRIVATE

    def test_does_not_accept_server_controlled_fields(self) -> None:
        """`id`/`created_by` are never part of the request schema — a
        client-supplied value for either is silently ignored rather than
        raising, since `ORJSONModel` doesn't forbid extra fields; the
        mass-assignment protection is that these fields simply don't
        exist on the model, so nothing downstream ever reads them."""
        request = CreateCommunityRequest.model_validate(
            {"slug": "oncology", "name": "Oncology", "id": "ignored", "created_by": "ignored"}
        )
        assert not hasattr(request, "id")
        assert not hasattr(request, "created_by")

    def test_rejects_unknown_visibility_value(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRequest.model_validate(
                {"slug": "oncology", "name": "Oncology", "visibility": "not-a-real-value"}
            )


class TestUpdateCommunityRequest:
    def test_all_fields_optional(self) -> None:
        request = UpdateCommunityRequest()
        assert request.name is None
        assert request.description is None
        assert request.clear_description is False
        assert request.visibility is None

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCommunityRequest(name="")

    def test_name_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCommunityRequest(name="a" * 201)

    def test_description_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCommunityRequest(description="a" * 2001)

    def test_valid_partial_update_is_accepted(self) -> None:
        request = UpdateCommunityRequest(visibility=CommunityVisibility.VERIFIED_ONLY)
        assert request.visibility is CommunityVisibility.VERIFIED_ONLY

    def test_clear_description_flag_is_accepted(self) -> None:
        request = UpdateCommunityRequest(clear_description=True)
        assert request.clear_description is True

    def test_category_id_and_clear_category_default(self) -> None:
        request = UpdateCommunityRequest()
        assert request.category_id is None
        assert request.clear_category is False

    def test_accepts_a_category_id(self) -> None:
        category_id = uuid4()
        request = UpdateCommunityRequest(category_id=category_id)
        assert request.category_id == category_id


class TestCommunityResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        now = datetime.now(UTC)
        response = CommunityResponse(
            id=uuid4(),
            organization_id=uuid4(),
            slug="oncology",
            name="Oncology",
            visibility=CommunityVisibility.PUBLIC,
            created_at=now,
            updated_at=now,
        )
        assert response.slug == "oncology"
        assert response.description is None
        assert response.created_by is None
        assert response.category_id is None
        assert response.avatar_storage_path is None
        assert response.banner_storage_path is None
        assert response.is_verified is False
        assert response.is_featured is False

    def test_constructs_from_attributes(self) -> None:
        """`ORJSONModel.model_config` sets `from_attributes=True` — every
        response schema in this module is built from a plain
        `CommunitySummaryDTO`/`CommunityMemberSummaryDTO`, not a dict, at
        every real call site (see `presentation/router.py`)."""

        class _FakeSummary:
            id = uuid4()
            organization_id = uuid4()
            slug = "oncology"
            name = "Oncology"
            description = None
            visibility = CommunityVisibility.PUBLIC
            created_by = None
            created_at = datetime.now(UTC)
            updated_at = datetime.now(UTC)

        response = CommunityResponse.model_validate(_FakeSummary())
        assert response.slug == "oncology"


class TestCommunityMemberResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommunityMemberResponse(
            id=uuid4(),
            community_id=uuid4(),
            user_id=uuid4(),
            role=CommunityRole.ADMIN,
            status=CommunityMemberStatus.ACTIVE,
            joined_at=datetime.now(UTC),
        )
        assert response.role is CommunityRole.ADMIN
        assert response.status is CommunityMemberStatus.ACTIVE


class TestCommunitySearchResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = CommunitySearchResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0


class TestSetCommunityFeaturedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetCommunityFeaturedRequest(featured=True).featured is True

    def test_featured_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetCommunityFeaturedRequest.model_validate({})


class TestSetCommunityVerifiedRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetCommunityVerifiedRequest(verified=True).verified is True

    def test_verified_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetCommunityVerifiedRequest.model_validate({})


class TestCommunityCategoryResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommunityCategoryResponse(
            id=uuid4(), name="Oncology", slug="oncology", is_active=True
        )
        assert response.name == "Oncology"
        assert response.description is None


class TestCreateCommunityCategoryRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateCommunityCategoryRequest(name="Oncology", slug="oncology")
        assert request.name == "Oncology"
        assert request.description is None

    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityCategoryRequest(name="", slug="oncology")

    def test_name_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityCategoryRequest(name="a" * 101, slug="oncology")

    def test_slug_too_short_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityCategoryRequest(name="Oncology", slug="ab")

    @pytest.mark.parametrize("slug", ["Oncology", "onco_logy", "onco logy", "-oncology"])
    def test_slug_pattern_violations_are_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityCategoryRequest(name="Oncology", slug=slug)

    def test_description_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityCategoryRequest(name="Oncology", slug="oncology", description="a" * 1001)


class TestCommunityTagResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommunityTagResponse(id=uuid4(), name="diabetes")
        assert response.name == "diabetes"


class TestAssignCommunityTagRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = AssignCommunityTagRequest(tag_name="diabetes")
        assert request.tag_name == "diabetes"

    def test_blank_tag_name_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssignCommunityTagRequest(tag_name="")

    def test_tag_name_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssignCommunityTagRequest(tag_name="a" * 51)


class TestCommunityTagSearchResponse:
    def test_constructs_with_an_empty_result_set(self) -> None:
        response = CommunityTagSearchResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0


class TestCommunityRuleResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommunityRuleResponse(
            id=uuid4(), community_id=uuid4(), title="Be respectful", position=0, is_enabled=True
        )
        assert response.title == "Be respectful"
        assert response.description is None


class TestCreateCommunityRuleRequest:
    def test_valid_request_is_accepted(self) -> None:
        request = CreateCommunityRuleRequest(title="Be respectful")
        assert request.title == "Be respectful"
        assert request.description is None

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRuleRequest(title="")

    def test_title_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRuleRequest(title="a" * 201)

    def test_description_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateCommunityRuleRequest(title="Be respectful", description="a" * 2001)


class TestUpdateCommunityRuleRequest:
    def test_all_fields_optional(self) -> None:
        request = UpdateCommunityRuleRequest()
        assert request.title is None
        assert request.description is None

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCommunityRuleRequest(title="")

    def test_title_too_long_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpdateCommunityRuleRequest(title="a" * 201)


class TestSetCommunityRuleEnabledRequest:
    def test_accepts_a_boolean(self) -> None:
        assert SetCommunityRuleEnabledRequest(enabled=False).enabled is False

    def test_enabled_is_required(self) -> None:
        with pytest.raises(ValidationError):
            SetCommunityRuleEnabledRequest.model_validate({})


class TestReorderCommunityRulesRequest:
    def test_accepts_a_list_of_rule_ids(self) -> None:
        rule_ids = [uuid4(), uuid4()]
        request = ReorderCommunityRulesRequest(ordered_rule_ids=rule_ids)
        assert request.ordered_rule_ids == rule_ids

    def test_accepts_an_empty_list(self) -> None:
        request = ReorderCommunityRulesRequest(ordered_rule_ids=[])
        assert request.ordered_rule_ids == []

    def test_ordered_rule_ids_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ReorderCommunityRulesRequest.model_validate({})


class TestCommunityStatisticsResponse:
    def test_constructs_from_a_full_field_set(self) -> None:
        response = CommunityStatisticsResponse(
            community_id=uuid4(),
            member_count=5,
            moderator_count=2,
            rule_count=3,
            tag_count=4,
            is_verified=True,
            is_featured=False,
            created_at=datetime.now(UTC),
        )
        assert response.member_count == 5
        assert response.is_verified is True
