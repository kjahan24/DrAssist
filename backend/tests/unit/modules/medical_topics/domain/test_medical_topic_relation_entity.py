"""Tests for the `MedicalTopicRelation` aggregate root."""

from uuid import uuid4

from app.modules.medical_topics.domain.entities import MedicalTopicRelation
from app.modules.medical_topics.domain.enums import TopicRelationType
from app.modules.medical_topics.domain.events import MedicalTopicRelationCreated
from app.modules.medical_topics.domain.exceptions import TopicCannotRelateToItselfError
from app.modules.medical_topics.domain.value_objects import TopicId


def _topic_id() -> TopicId:
    return TopicId(uuid4())


class TestMedicalTopicRelationCreate:
    def test_sets_required_fields(self) -> None:
        topic_id = _topic_id()
        related_topic_id = uuid4()
        relation = MedicalTopicRelation.create(topic_id=topic_id, related_topic_id=related_topic_id)
        assert relation.topic_id == topic_id
        assert relation.related_topic_id == related_topic_id

    def test_defaults_to_related_relation_type(self) -> None:
        relation = MedicalTopicRelation.create(topic_id=_topic_id(), related_topic_id=uuid4())
        assert relation.relation_type is TopicRelationType.RELATED

    def test_accepts_explicit_relation_type(self) -> None:
        relation = MedicalTopicRelation.create(
            topic_id=_topic_id(),
            related_topic_id=uuid4(),
            relation_type=TopicRelationType.SEE_ALSO,
        )
        assert relation.relation_type is TopicRelationType.SEE_ALSO

    def test_relating_a_topic_to_itself_raises(self) -> None:
        topic_id = _topic_id()
        try:
            MedicalTopicRelation.create(topic_id=topic_id, related_topic_id=topic_id.value)
            raised = False
        except TopicCannotRelateToItselfError:
            raised = True
        assert raised is True

    def test_assigns_a_unique_id(self) -> None:
        topic_id = _topic_id()
        first = MedicalTopicRelation.create(topic_id=topic_id, related_topic_id=uuid4())
        second = MedicalTopicRelation.create(topic_id=topic_id, related_topic_id=uuid4())
        assert first.id != second.id

    def test_records_a_medical_topic_relation_created_event(self) -> None:
        topic_id = _topic_id()
        related_topic_id = uuid4()
        relation = MedicalTopicRelation.create(topic_id=topic_id, related_topic_id=related_topic_id)
        events = relation.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, MedicalTopicRelationCreated)
        assert event.relation_id == relation.id
        assert event.topic_id == topic_id.value
        assert event.related_topic_id == related_topic_id

    def test_pull_events_drains_the_queue(self) -> None:
        relation = MedicalTopicRelation.create(topic_id=_topic_id(), related_topic_id=uuid4())
        relation.pull_events()
        assert relation.pull_events() == []
