"""Tests for the `MedicalTopic` aggregate root."""

from uuid import uuid4

from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.events import (
    MedicalTopicCreated,
    MedicalTopicFeaturedChanged,
    MedicalTopicUpdated,
)
from app.modules.medical_topics.domain.exceptions import (
    NegativeTopicScoreError,
    TopicCannotBeOwnParentError,
)
from app.modules.medical_topics.domain.value_objects import (
    TopicColor,
    TopicDescription,
    TopicName,
    TopicSlug,
)


def _slug() -> TopicSlug:
    return TopicSlug("cardiac-arrhythmia")


def _name() -> TopicName:
    return TopicName("Cardiac Arrhythmia")


class TestMedicalTopicCreate:
    def test_sets_required_fields(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.slug == _slug()
        assert topic.name == _name()

    def test_defaults_to_draft_status(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.status is TopicStatus.DRAFT

    def test_defaults_to_public_visibility(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.visibility is TopicVisibility.PUBLIC

    def test_accepts_explicit_visibility(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name(), visibility=TopicVisibility.PRIVATE)
        assert topic.visibility is TopicVisibility.PRIVATE

    def test_defaults_description_to_none(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.description is None

    def test_accepts_explicit_description(self) -> None:
        description = TopicDescription("Covers irregular heart rhythms.")
        topic = MedicalTopic.create(slug=_slug(), name=_name(), description=description)
        assert topic.description == description

    def test_defaults_icon_and_color_to_none(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.icon is None
        assert topic.color is None

    def test_accepts_explicit_icon_and_color(self) -> None:
        topic = MedicalTopic.create(
            slug=_slug(), name=_name(), icon="heart-pulse", color=TopicColor("#FF5733")
        )
        assert topic.icon == "heart-pulse"
        assert topic.color == TopicColor("#FF5733")

    def test_defaults_parent_and_specialty_to_none(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.parent_id is None
        assert topic.specialty_id is None

    def test_accepts_explicit_parent_and_specialty(self) -> None:
        parent_id, specialty_id = uuid4(), uuid4()
        topic = MedicalTopic.create(
            slug=_slug(), name=_name(), parent_id=parent_id, specialty_id=specialty_id
        )
        assert topic.parent_id == parent_id
        assert topic.specialty_id == specialty_id

    def test_defaults_to_not_featured(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.is_featured is False

    def test_defaults_scores_to_zero(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.trending_score == 0.0
        assert topic.popularity_score == 0.0

    def test_no_creator_leaves_created_by_and_updated_by_none(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        assert topic.created_by is None
        assert topic.updated_by is None

    def test_created_by_sets_both_created_by_and_updated_by(self) -> None:
        creator_id = uuid4()
        topic = MedicalTopic.create(slug=_slug(), name=_name(), created_by=creator_id)
        assert topic.created_by == creator_id
        assert topic.updated_by == creator_id

    def test_assigns_a_unique_id(self) -> None:
        first = MedicalTopic.create(slug=_slug(), name=_name())
        second = MedicalTopic.create(slug=TopicSlug("other"), name=_name())
        assert first.id != second.id

    def test_records_a_medical_topic_created_event(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        events = topic.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MedicalTopicCreated)
        assert event.topic_id == topic.id
        assert event.slug == "cardiac-arrhythmia"
        assert event.name == "Cardiac Arrhythmia"

    def test_pull_events_drains_the_queue(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.pull_events()
        assert topic.pull_events() == []


class TestMedicalTopicUpdateProfile:
    def test_updates_name(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        new_name = TopicName("Renamed Topic")
        topic.update_profile(name=new_name)
        assert topic.name == new_name

    def test_updates_status(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.update_profile(status=TopicStatus.PUBLISHED)
        assert topic.status is TopicStatus.PUBLISHED

    def test_updates_visibility(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.update_profile(visibility=TopicVisibility.UNLISTED)
        assert topic.visibility is TopicVisibility.UNLISTED

    def test_updates_description(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        new_description = TopicDescription("Updated description.")
        topic.update_profile(description=new_description)
        assert topic.description == new_description

    def test_clear_description_removes_an_existing_description(self) -> None:
        topic = MedicalTopic.create(
            slug=_slug(), name=_name(), description=TopicDescription("Original.")
        )
        topic.update_profile(clear_description=True)
        assert topic.description is None

    def test_clear_description_takes_precedence_over_a_given_description(self) -> None:
        topic = MedicalTopic.create(
            slug=_slug(), name=_name(), description=TopicDescription("Original.")
        )
        topic.update_profile(
            description=TopicDescription("New description."), clear_description=True
        )
        assert topic.description is None

    def test_updates_icon(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.update_profile(icon="heart-pulse")
        assert topic.icon == "heart-pulse"

    def test_clear_icon_removes_an_existing_icon(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name(), icon="heart-pulse")
        topic.update_profile(clear_icon=True)
        assert topic.icon is None

    def test_updates_color(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        color = TopicColor("#FF5733")
        topic.update_profile(color=color)
        assert topic.color == color

    def test_clear_color_removes_an_existing_color(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name(), color=TopicColor("#FF5733"))
        topic.update_profile(clear_color=True)
        assert topic.color is None

    def test_assigns_a_parent(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        parent_id = uuid4()
        topic.update_profile(parent_id=parent_id)
        assert topic.parent_id == parent_id

    def test_clear_parent_removes_an_existing_parent(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name(), parent_id=uuid4())
        topic.update_profile(clear_parent=True)
        assert topic.parent_id is None

    def test_clear_parent_takes_precedence_over_a_given_parent(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.update_profile(parent_id=uuid4(), clear_parent=True)
        assert topic.parent_id is None

    def test_setting_parent_to_self_raises(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        try:
            topic.update_profile(parent_id=topic.id)
            raised = False
        except TopicCannotBeOwnParentError:
            raised = True
        assert raised is True

    def test_assigns_a_specialty(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        specialty_id = uuid4()
        topic.update_profile(specialty_id=specialty_id)
        assert topic.specialty_id == specialty_id

    def test_clear_specialty_removes_an_existing_specialty(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name(), specialty_id=uuid4())
        topic.update_profile(clear_specialty=True)
        assert topic.specialty_id is None

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        original_name = topic.name
        original_status = topic.status
        topic.update_profile()
        assert topic.name == original_name
        assert topic.status == original_status

    def test_updates_updated_by(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        updater_id = uuid4()
        topic.update_profile(updated_by=updater_id)
        assert topic.updated_by == updater_id

    def test_updates_updated_at_timestamp(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        before = topic.updated_at
        topic.update_profile(name=TopicName("New Name"))
        assert topic.updated_at >= before

    def test_records_a_medical_topic_updated_event(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.pull_events()
        topic.update_profile(name=TopicName("New Name"))
        events = topic.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MedicalTopicUpdated)
        assert event.topic_id == topic.id


class TestMedicalTopicSetFeatured:
    def test_sets_featured_true(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.set_featured(True)
        assert topic.is_featured is True

    def test_sets_featured_false(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.set_featured(True)
        topic.set_featured(False)
        assert topic.is_featured is False

    def test_records_a_medical_topic_featured_changed_event(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.pull_events()
        topic.set_featured(True)
        events = topic.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MedicalTopicFeaturedChanged)
        assert event.topic_id == topic.id
        assert event.is_featured is True

    def test_setting_the_same_value_is_a_no_op_and_records_no_event(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.pull_events()
        topic.set_featured(False)
        assert topic.pull_events() == []


class TestMedicalTopicUpdateTrendingScore:
    def test_updates_the_score(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.update_trending_score(42.5)
        assert topic.trending_score == 42.5

    def test_updates_updated_at_timestamp(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        before = topic.updated_at
        topic.update_trending_score(10.0)
        assert topic.updated_at >= before

    def test_negative_score_raises(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        try:
            topic.update_trending_score(-1.0)
            raised = False
        except NegativeTopicScoreError:
            raised = True
        assert raised is True

    def test_records_no_domain_event(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.pull_events()
        topic.update_trending_score(10.0)
        assert topic.pull_events() == []


class TestMedicalTopicUpdatePopularityScore:
    def test_updates_the_score(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.update_popularity_score(99.9)
        assert topic.popularity_score == 99.9

    def test_negative_score_raises(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        try:
            topic.update_popularity_score(-5.0)
            raised = False
        except NegativeTopicScoreError:
            raised = True
        assert raised is True

    def test_records_no_domain_event(self) -> None:
        topic = MedicalTopic.create(slug=_slug(), name=_name())
        topic.pull_events()
        topic.update_popularity_score(10.0)
        assert topic.pull_events() == []
