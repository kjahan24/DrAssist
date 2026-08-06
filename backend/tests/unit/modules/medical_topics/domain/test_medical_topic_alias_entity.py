"""Tests for the `MedicalTopicAlias` aggregate root."""

from uuid import uuid4

from app.modules.medical_topics.domain.entities import MedicalTopicAlias
from app.modules.medical_topics.domain.events import MedicalTopicAliasCreated
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName


def _topic_id() -> TopicId:
    return TopicId(uuid4())


def _alias() -> TopicName:
    return TopicName("heart arrhythmia")


class TestMedicalTopicAliasCreate:
    def test_sets_required_fields(self) -> None:
        topic_id = _topic_id()
        alias = MedicalTopicAlias.create(topic_id=topic_id, alias=_alias())
        assert alias.topic_id == topic_id
        assert alias.alias == _alias()

    def test_assigns_a_unique_id(self) -> None:
        topic_id = _topic_id()
        first = MedicalTopicAlias.create(topic_id=topic_id, alias=_alias())
        second = MedicalTopicAlias.create(topic_id=topic_id, alias=TopicName("irregular heartbeat"))
        assert first.id != second.id

    def test_records_a_medical_topic_alias_created_event(self) -> None:
        topic_id = _topic_id()
        alias = MedicalTopicAlias.create(topic_id=topic_id, alias=_alias())
        events = alias.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MedicalTopicAliasCreated)
        assert event.alias_id == alias.id
        assert event.topic_id == topic_id.value
        assert event.alias == "heart arrhythmia"

    def test_pull_events_drains_the_queue(self) -> None:
        alias = MedicalTopicAlias.create(topic_id=_topic_id(), alias=_alias())
        alias.pull_events()
        assert alias.pull_events() == []
