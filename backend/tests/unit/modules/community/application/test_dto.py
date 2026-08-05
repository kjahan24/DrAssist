"""Tests for the Community module's application-layer DTOs — plain,
immutable dataclass construction and field defaults."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.community.application.dto import (
    AssignCommunityTagInput,
    BrowseCommunitiesInput,
    BrowseCommunitiesOutput,
    CommunityCategorySummaryDTO,
    CommunityMemberSummaryDTO,
    CommunityRuleSummaryDTO,
    CommunityStatisticsDTO,
    CommunitySummaryDTO,
    CommunityTagSummaryDTO,
    CreateCommunityCategoryInput,
    CreateCommunityCategoryOutput,
    CreateCommunityInput,
    CreateCommunityOutput,
    CreateCommunityRuleInput,
    CreateCommunityRuleOutput,
    DeleteCommunityInput,
    DeleteCommunityRuleInput,
    JoinCommunityInput,
    JoinCommunityOutput,
    LeaveCommunityInput,
    ListCommunitiesOutput,
    ListFeaturedCommunitiesInput,
    ReorderCommunityRulesInput,
    SearchCommunitiesInput,
    SearchCommunitiesOutput,
    SearchCommunityTagsInput,
    SearchCommunityTagsOutput,
    SetCommunityFeaturedInput,
    SetCommunityRuleEnabledInput,
    SetCommunityVerifiedInput,
    UnassignCommunityTagInput,
    UpdateCommunityAppearanceInput,
    UpdateCommunityAppearanceOutput,
    UpdateCommunityInput,
    UpdateCommunityOutput,
    UpdateCommunityRuleInput,
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
        assert input_dto.category_id is None
        assert input_dto.clear_category is False


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
        assert summary.category_id is None
        assert summary.avatar_storage_path is None
        assert summary.banner_storage_path is None
        assert summary.is_verified is False
        assert summary.is_featured is False


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


class TestBrowseCommunitiesInput:
    def test_defaults(self) -> None:
        input_dto = BrowseCommunitiesInput(organization_id=uuid4())
        assert input_dto.category_id is None
        assert input_dto.tag_ids == ()
        assert input_dto.visibilities is None
        assert input_dto.sort == "recent"
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestBrowseCommunitiesOutput:
    def test_construction(self) -> None:
        output = BrowseCommunitiesOutput(items=(), total=0)
        assert output.items == ()
        assert output.total == 0


class TestSearchCommunitiesInput:
    def test_defaults(self) -> None:
        input_dto = SearchCommunitiesInput(organization_id=uuid4(), query="oncology")
        assert input_dto.category_id is None
        assert input_dto.tag_ids == ()
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestSearchCommunitiesOutput:
    def test_construction(self) -> None:
        output = SearchCommunitiesOutput(items=(), total=0)
        assert output.items == ()
        assert output.total == 0


class TestListFeaturedCommunitiesInput:
    def test_defaults(self) -> None:
        input_dto = ListFeaturedCommunitiesInput(organization_id=uuid4())
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestSetCommunityFeaturedInput:
    def test_construction(self) -> None:
        community_id = uuid4()
        input_dto = SetCommunityFeaturedInput(community_id=community_id, featured=True)
        assert input_dto.community_id == community_id
        assert input_dto.featured is True


class TestSetCommunityVerifiedInput:
    def test_construction(self) -> None:
        community_id = uuid4()
        input_dto = SetCommunityVerifiedInput(community_id=community_id, verified=True)
        assert input_dto.community_id == community_id
        assert input_dto.verified is True


class TestUpdateCommunityAppearanceInput:
    def test_defaults(self) -> None:
        input_dto = UpdateCommunityAppearanceInput(community_id=uuid4(), acting_user_id=uuid4())
        assert input_dto.avatar_data is None
        assert input_dto.clear_avatar is False
        assert input_dto.banner_data is None
        assert input_dto.clear_banner is False


class TestUpdateCommunityAppearanceOutput:
    def test_construction(self) -> None:
        community_id = uuid4()
        output = UpdateCommunityAppearanceOutput(
            community_id=community_id, avatar_storage_path="path/a.png", banner_storage_path=None
        )
        assert output.community_id == community_id
        assert output.avatar_storage_path == "path/a.png"
        assert output.banner_storage_path is None


class TestCommunityCategorySummaryDTO:
    def test_id_property_aliases_category_id(self) -> None:
        category_id = uuid4()
        summary = CommunityCategorySummaryDTO(
            category_id=category_id, name="Oncology", slug="oncology", is_active=True
        )
        assert summary.id == category_id

    def test_description_defaults_to_none(self) -> None:
        summary = CommunityCategorySummaryDTO(
            category_id=uuid4(), name="Oncology", slug="oncology", is_active=True
        )
        assert summary.description is None


class TestCreateCommunityCategoryInput:
    def test_defaults(self) -> None:
        input_dto = CreateCommunityCategoryInput(name="Oncology", slug="oncology")
        assert input_dto.description is None


class TestCreateCommunityCategoryOutput:
    def test_construction(self) -> None:
        category_id = uuid4()
        output = CreateCommunityCategoryOutput(
            category_id=category_id, name="Oncology", slug="oncology"
        )
        assert output.category_id == category_id
        assert output.name == "Oncology"


class TestCommunityTagSummaryDTO:
    def test_id_property_aliases_tag_id(self) -> None:
        tag_id = uuid4()
        summary = CommunityTagSummaryDTO(tag_id=tag_id, name="diabetes")
        assert summary.id == tag_id


class TestAssignCommunityTagInput:
    def test_construction(self) -> None:
        community_id, acting_user_id = uuid4(), uuid4()
        input_dto = AssignCommunityTagInput(
            community_id=community_id, acting_user_id=acting_user_id, tag_name="diabetes"
        )
        assert input_dto.community_id == community_id
        assert input_dto.tag_name == "diabetes"


class TestUnassignCommunityTagInput:
    def test_construction(self) -> None:
        community_id, acting_user_id, tag_id = uuid4(), uuid4(), uuid4()
        input_dto = UnassignCommunityTagInput(
            community_id=community_id, acting_user_id=acting_user_id, tag_id=tag_id
        )
        assert input_dto.tag_id == tag_id


class TestSearchCommunityTagsInput:
    def test_defaults(self) -> None:
        input_dto = SearchCommunityTagsInput(query="diabetes")
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestSearchCommunityTagsOutput:
    def test_construction(self) -> None:
        output = SearchCommunityTagsOutput(items=(), total=0)
        assert output.items == ()
        assert output.total == 0


class TestCommunityRuleSummaryDTO:
    def test_id_property_aliases_rule_id(self) -> None:
        rule_id = uuid4()
        summary = CommunityRuleSummaryDTO(
            rule_id=rule_id,
            community_id=uuid4(),
            title="Be respectful",
            position=0,
            is_enabled=True,
        )
        assert summary.id == rule_id

    def test_description_defaults_to_none(self) -> None:
        summary = CommunityRuleSummaryDTO(
            rule_id=uuid4(),
            community_id=uuid4(),
            title="Be respectful",
            position=0,
            is_enabled=True,
        )
        assert summary.description is None


class TestCreateCommunityRuleInput:
    def test_defaults(self) -> None:
        input_dto = CreateCommunityRuleInput(
            community_id=uuid4(), acting_user_id=uuid4(), title="Be respectful"
        )
        assert input_dto.description is None


class TestCreateCommunityRuleOutput:
    def test_construction(self) -> None:
        rule_id = uuid4()
        output = CreateCommunityRuleOutput(
            rule_id=rule_id, community_id=uuid4(), title="Be respectful", position=0
        )
        assert output.rule_id == rule_id
        assert output.position == 0


class TestUpdateCommunityRuleInput:
    def test_defaults(self) -> None:
        input_dto = UpdateCommunityRuleInput(
            rule_id=uuid4(), community_id=uuid4(), acting_user_id=uuid4()
        )
        assert input_dto.title is None
        assert input_dto.description is None


class TestSetCommunityRuleEnabledInput:
    def test_construction(self) -> None:
        rule_id = uuid4()
        input_dto = SetCommunityRuleEnabledInput(
            rule_id=rule_id, community_id=uuid4(), acting_user_id=uuid4(), enabled=False
        )
        assert input_dto.rule_id == rule_id
        assert input_dto.enabled is False


class TestDeleteCommunityRuleInput:
    def test_construction(self) -> None:
        rule_id = uuid4()
        input_dto = DeleteCommunityRuleInput(
            rule_id=rule_id, community_id=uuid4(), acting_user_id=uuid4()
        )
        assert input_dto.rule_id == rule_id


class TestReorderCommunityRulesInput:
    def test_defaults_to_an_empty_order(self) -> None:
        input_dto = ReorderCommunityRulesInput(community_id=uuid4(), acting_user_id=uuid4())
        assert input_dto.ordered_rule_ids == ()


class TestCommunityStatisticsDTO:
    def test_construction(self) -> None:
        community_id = uuid4()
        stats = CommunityStatisticsDTO(
            community_id=community_id,
            member_count=5,
            moderator_count=2,
            rule_count=3,
            tag_count=4,
            is_verified=True,
            is_featured=False,
            created_at=datetime.now(UTC),
        )
        assert stats.community_id == community_id
        assert stats.member_count == 5
        assert stats.is_verified is True
