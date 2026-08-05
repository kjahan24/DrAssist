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
    CommunityMemberResponse,
    CommunityResponse,
    CreateCommunityRequest,
    UpdateCommunityRequest,
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
