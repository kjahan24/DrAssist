"""Tests for the Community module's application-layer DTOs — plain,
immutable dataclass construction and field defaults."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.community.application.dto import (
    CommunityMemberSummaryDTO,
    CommunitySummaryDTO,
    CreateCommunityInput,
    CreateCommunityOutput,
    DeleteCommunityInput,
    JoinCommunityInput,
    JoinCommunityOutput,
    LeaveCommunityInput,
    ListCommunitiesOutput,
    UpdateCommunityInput,
    UpdateCommunityOutput,
)
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)


class TestCreateCommunityInput:
    def test_defaults(self) -> None:
        input_dto = CreateCommunityInput(
            organization_id=uuid4(), slug="oncology", name="Oncology", created_by=uuid4()
        )
        assert input_dto.description is None
        assert input_dto.visibility is CommunityVisibility.PUBLIC

    def test_is_frozen(self) -> None:
        input_dto = CreateCommunityInput(
            organization_id=uuid4(), slug="oncology", name="Oncology", created_by=uuid4()
        )
        try:
            input_dto.slug = "changed"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised is True


class TestCreateCommunityOutput:
    def test_construction(self) -> None:
        output = CreateCommunityOutput(
            community_id=uuid4(),
            organization_id=uuid4(),
            slug="oncology",
            name="Oncology",
            visibility=CommunityVisibility.PUBLIC,
        )
        assert output.slug == "oncology"


class TestUpdateCommunityInput:
    def test_defaults(self) -> None:
        input_dto = UpdateCommunityInput(community_id=uuid4(), acting_user_id=uuid4())
        assert input_dto.name is None
        assert input_dto.description is None
        assert input_dto.clear_description is False
        assert input_dto.visibility is None


class TestUpdateCommunityOutput:
    def test_construction(self) -> None:
        output = UpdateCommunityOutput(
            community_id=uuid4(), name="Renamed", visibility=CommunityVisibility.PRIVATE
        )
        assert output.name == "Renamed"


class TestDeleteCommunityInput:
    def test_construction(self) -> None:
        community_id, acting_user_id = uuid4(), uuid4()
        input_dto = DeleteCommunityInput(community_id=community_id, acting_user_id=acting_user_id)
        assert input_dto.community_id == community_id
        assert input_dto.acting_user_id == acting_user_id


class TestJoinCommunityInput:
    def test_construction(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        input_dto = JoinCommunityInput(community_id=community_id, user_id=user_id)
        assert input_dto.community_id == community_id
        assert input_dto.user_id == user_id


class TestJoinCommunityOutput:
    def test_construction(self) -> None:
        output = JoinCommunityOutput(
            member_id=uuid4(),
            community_id=uuid4(),
            user_id=uuid4(),
            role=CommunityRole.MEMBER,
            status=CommunityMemberStatus.ACTIVE,
            joined_at=datetime.now(UTC),
        )
        assert output.role is CommunityRole.MEMBER
        assert output.status is CommunityMemberStatus.ACTIVE


class TestLeaveCommunityInput:
    def test_construction(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        input_dto = LeaveCommunityInput(community_id=community_id, user_id=user_id)
        assert input_dto.community_id == community_id
        assert input_dto.user_id == user_id


class TestCommunitySummaryDTO:
    def test_id_property_aliases_community_id(self) -> None:
        community_id = uuid4()
        summary = CommunitySummaryDTO(
            community_id=community_id,
            organization_id=uuid4(),
            slug="oncology",
            name="Oncology",
            visibility=CommunityVisibility.PUBLIC,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert summary.id == community_id

    def test_optional_fields_default_to_none(self) -> None:
        summary = CommunitySummaryDTO(
            community_id=uuid4(),
            organization_id=uuid4(),
            slug="oncology",
            name="Oncology",
            visibility=CommunityVisibility.PUBLIC,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert summary.description is None
        assert summary.created_by is None


class TestCommunityMemberSummaryDTO:
    def test_id_property_aliases_member_id(self) -> None:
        member_id = uuid4()
        summary = CommunityMemberSummaryDTO(
            member_id=member_id,
            community_id=uuid4(),
            user_id=uuid4(),
            role=CommunityRole.MEMBER,
            status=CommunityMemberStatus.ACTIVE,
            joined_at=datetime.now(UTC),
        )
        assert summary.id == member_id


class TestListCommunitiesOutput:
    def test_construction(self) -> None:
        output = ListCommunitiesOutput(items=(), total=0)
        assert output.items == ()
        assert output.total == 0
