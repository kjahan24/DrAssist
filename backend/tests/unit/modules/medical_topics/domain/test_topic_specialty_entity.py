"""Tests for the `TopicSpecialty` aggregate root."""

from app.modules.medical_topics.domain.entities import TopicSpecialty
from app.modules.medical_topics.domain.events import TopicSpecialtyCreated
from app.modules.medical_topics.domain.value_objects import TopicDescription, TopicName, TopicSlug


def _name() -> TopicName:
    return TopicName("Oncology")


def _slug() -> TopicSlug:
    return TopicSlug("oncology")


class TestTopicSpecialtyCreate:
    def test_sets_required_fields(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        assert specialty.name == _name()
        assert specialty.slug == _slug()

    def test_defaults_description_to_none(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        assert specialty.description is None

    def test_accepts_explicit_description(self) -> None:
        description = TopicDescription("Cancer care and treatment.")
        specialty = TopicSpecialty.create(name=_name(), slug=_slug(), description=description)
        assert specialty.description == description

    def test_defaults_to_active(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        assert specialty.is_active is True

    def test_assigns_a_unique_id(self) -> None:
        first = TopicSpecialty.create(name=_name(), slug=_slug())
        second = TopicSpecialty.create(name=TopicName("Dermatology"), slug=TopicSlug("dermatology"))
        assert first.id != second.id

    def test_records_a_topic_specialty_created_event(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        events = specialty.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, TopicSpecialtyCreated)
        assert event.specialty_id == specialty.id
        assert event.name == "Oncology"

    def test_pull_events_drains_the_queue(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        specialty.pull_events()
        assert specialty.pull_events() == []


class TestTopicSpecialtyDeactivate:
    def test_sets_is_active_false(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        specialty.deactivate()
        assert specialty.is_active is False

    def test_updates_updated_at_timestamp(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        before = specialty.updated_at
        specialty.deactivate()
        assert specialty.updated_at >= before


class TestTopicSpecialtyActivate:
    def test_sets_is_active_true(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        specialty.deactivate()
        specialty.activate()
        assert specialty.is_active is True

    def test_activating_an_already_active_specialty_stays_active(self) -> None:
        specialty = TopicSpecialty.create(name=_name(), slug=_slug())
        specialty.activate()
        assert specialty.is_active is True
