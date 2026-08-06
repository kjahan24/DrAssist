"""Tests for the Medical Topics module's application-layer DTOs — plain,
immutable dataclass construction and field defaults."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.medical_topics.application.dto import (
    CreateTopicAliasInput,
    CreateTopicInput,
    CreateTopicOutput,
    CreateTopicRelationInput,
    CreateTopicSpecialtyInput,
    CreateTopicSpecialtyOutput,
    DeleteTopicAliasInput,
    DeleteTopicInput,
    DeleteTopicRelationInput,
    FeaturedTopicsInput,
    FollowTopicInput,
    FollowTopicOutput,
    ListTopicsInput,
    ListTopicsOutput,
    RelatedTopicsInput,
    RelatedTopicsOutput,
    SearchTopicsInput,
    SearchTopicsOutput,
    SetTopicFeaturedInput,
    TopicAliasSummaryDTO,
    TopicFollowerSummaryDTO,
    TopicRelationSummaryDTO,
    TopicSpecialtySummaryDTO,
    TopicSummaryDTO,
    TrendingTopicsInput,
    UnfollowTopicInput,
    UpdateTopicInput,
    UpdateTopicOutput,
)
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility


class TestCreateTopicInput:
    def test_defaults(self) -> None:
        input_dto = CreateTopicInput(slug="oncology", name="Oncology")
        assert input_dto.description is None
        assert input_dto.visibility is TopicVisibility.PUBLIC

    def test_is_frozen(self) -> None:
        input_dto = CreateTopicInput(slug="oncology", name="Oncology")
        try:
            input_dto.slug = "changed"  # type: ignore[misc]
            raised = False
        except AttributeError:
            raised = True
        assert raised is True


class TestCreateTopicOutput:
    def test_construction(self) -> None:
        output = CreateTopicOutput(
            topic_id=uuid4(),
            slug="oncology",
            name="Oncology",
            status=TopicStatus.DRAFT,
            visibility=TopicVisibility.PUBLIC,
        )
        assert output.slug == "oncology"


class TestUpdateTopicInput:
    def test_defaults(self) -> None:
        input_dto = UpdateTopicInput(topic_id=uuid4())
        assert input_dto.name is None
        assert input_dto.description is None
        assert input_dto.clear_description is False
        assert input_dto.status is None
        assert input_dto.visibility is None
        assert input_dto.parent_id is None
        assert input_dto.clear_parent is False
        assert input_dto.specialty_id is None
        assert input_dto.clear_specialty is False


class TestUpdateTopicOutput:
    def test_construction(self) -> None:
        output = UpdateTopicOutput(
            topic_id=uuid4(),
            name="Renamed",
            status=TopicStatus.PUBLISHED,
            visibility=TopicVisibility.PRIVATE,
        )
        assert output.name == "Renamed"


class TestDeleteTopicInput:
    def test_construction(self) -> None:
        topic_id = uuid4()
        input_dto = DeleteTopicInput(topic_id=topic_id)
        assert input_dto.topic_id == topic_id


class TestFollowTopicInput:
    def test_construction(self) -> None:
        topic_id, user_id = uuid4(), uuid4()
        input_dto = FollowTopicInput(topic_id=topic_id, user_id=user_id)
        assert input_dto.topic_id == topic_id
        assert input_dto.user_id == user_id


class TestFollowTopicOutput:
    def test_construction(self) -> None:
        output = FollowTopicOutput(
            follower_id=uuid4(), topic_id=uuid4(), user_id=uuid4(), followed_at=datetime.now(UTC)
        )
        assert output.follower_id is not None


class TestUnfollowTopicInput:
    def test_construction(self) -> None:
        topic_id, user_id = uuid4(), uuid4()
        input_dto = UnfollowTopicInput(topic_id=topic_id, user_id=user_id)
        assert input_dto.topic_id == topic_id
        assert input_dto.user_id == user_id


class TestTopicSummaryDTO:
    def test_id_property_aliases_topic_id(self) -> None:
        topic_id = uuid4()
        summary = TopicSummaryDTO(
            topic_id=topic_id,
            slug="oncology",
            name="Oncology",
            status=TopicStatus.PUBLISHED,
            visibility=TopicVisibility.PUBLIC,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert summary.id == topic_id

    def test_optional_fields_default(self) -> None:
        summary = TopicSummaryDTO(
            topic_id=uuid4(),
            slug="oncology",
            name="Oncology",
            status=TopicStatus.PUBLISHED,
            visibility=TopicVisibility.PUBLIC,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert summary.description is None
        assert summary.icon is None
        assert summary.color is None
        assert summary.parent_id is None
        assert summary.specialty_id is None
        assert summary.is_featured is False
        assert summary.trending_score == 0.0
        assert summary.popularity_score == 0.0
        assert summary.created_by is None


class TestTopicFollowerSummaryDTO:
    def test_id_property_aliases_follower_id(self) -> None:
        follower_id = uuid4()
        summary = TopicFollowerSummaryDTO(
            follower_id=follower_id,
            topic_id=uuid4(),
            user_id=uuid4(),
            followed_at=datetime.now(UTC),
        )
        assert summary.id == follower_id


class TestListTopicsInput:
    def test_defaults(self) -> None:
        input_dto = ListTopicsInput()
        assert input_dto.query is None
        assert input_dto.status is None
        assert input_dto.visibility is None
        assert input_dto.specialty_id is None
        assert input_dto.parent_id is None
        assert input_dto.include_deleted is False
        assert input_dto.sort_by == "created_at"
        assert input_dto.sort_order == "asc"
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestListTopicsOutput:
    def test_construction(self) -> None:
        output = ListTopicsOutput(items=(), total=0)
        assert output.items == ()
        assert output.total == 0


class TestSearchTopicsInput:
    def test_defaults(self) -> None:
        input_dto = SearchTopicsInput(query="oncology")
        assert input_dto.specialty_id is None
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestSearchTopicsOutput:
    def test_construction(self) -> None:
        output = SearchTopicsOutput(items=(), total=0)
        assert output.items == ()
        assert output.total == 0


class TestTrendingTopicsInput:
    def test_defaults(self) -> None:
        input_dto = TrendingTopicsInput()
        assert input_dto.specialty_id is None
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestFeaturedTopicsInput:
    def test_defaults(self) -> None:
        input_dto = FeaturedTopicsInput()
        assert input_dto.offset == 0
        assert input_dto.limit == 20


class TestSetTopicFeaturedInput:
    def test_construction(self) -> None:
        topic_id = uuid4()
        input_dto = SetTopicFeaturedInput(topic_id=topic_id, featured=True)
        assert input_dto.topic_id == topic_id
        assert input_dto.featured is True


class TestRelatedTopicsInput:
    def test_defaults(self) -> None:
        topic_id = uuid4()
        input_dto = RelatedTopicsInput(topic_id=topic_id)
        assert input_dto.topic_id == topic_id
        assert input_dto.limit == 20


class TestRelatedTopicsOutput:
    def test_defaults_to_empty(self) -> None:
        output = RelatedTopicsOutput()
        assert output.items == ()


class TestTopicSpecialtySummaryDTO:
    def test_id_property_aliases_specialty_id(self) -> None:
        specialty_id = uuid4()
        summary = TopicSpecialtySummaryDTO(
            specialty_id=specialty_id, name="Oncology", slug="oncology", is_active=True
        )
        assert summary.id == specialty_id

    def test_description_defaults_to_none(self) -> None:
        summary = TopicSpecialtySummaryDTO(
            specialty_id=uuid4(), name="Oncology", slug="oncology", is_active=True
        )
        assert summary.description is None


class TestCreateTopicSpecialtyInput:
    def test_defaults(self) -> None:
        input_dto = CreateTopicSpecialtyInput(name="Oncology", slug="oncology")
        assert input_dto.description is None


class TestCreateTopicSpecialtyOutput:
    def test_construction(self) -> None:
        specialty_id = uuid4()
        output = CreateTopicSpecialtyOutput(
            specialty_id=specialty_id, name="Oncology", slug="oncology"
        )
        assert output.specialty_id == specialty_id


class TestTopicAliasSummaryDTO:
    def test_id_property_aliases_alias_id(self) -> None:
        alias_id = uuid4()
        summary = TopicAliasSummaryDTO(
            alias_id=alias_id, topic_id=uuid4(), alias="heart arrhythmia"
        )
        assert summary.id == alias_id


class TestCreateTopicAliasInput:
    def test_construction(self) -> None:
        topic_id = uuid4()
        input_dto = CreateTopicAliasInput(topic_id=topic_id, alias="heart arrhythmia")
        assert input_dto.topic_id == topic_id
        assert input_dto.alias == "heart arrhythmia"


class TestDeleteTopicAliasInput:
    def test_construction(self) -> None:
        alias_id = uuid4()
        input_dto = DeleteTopicAliasInput(alias_id=alias_id)
        assert input_dto.alias_id == alias_id


class TestTopicRelationSummaryDTO:
    def test_id_property_aliases_relation_id(self) -> None:
        relation_id = uuid4()
        summary = TopicRelationSummaryDTO(
            relation_id=relation_id,
            topic_id=uuid4(),
            related_topic_id=uuid4(),
            relation_type="related",
        )
        assert summary.id == relation_id


class TestCreateTopicRelationInput:
    def test_defaults(self) -> None:
        topic_id, related_topic_id = uuid4(), uuid4()
        input_dto = CreateTopicRelationInput(topic_id=topic_id, related_topic_id=related_topic_id)
        assert input_dto.relation_type == "related"


class TestDeleteTopicRelationInput:
    def test_construction(self) -> None:
        relation_id = uuid4()
        input_dto = DeleteTopicRelationInput(relation_id=relation_id)
        assert input_dto.relation_id == relation_id
