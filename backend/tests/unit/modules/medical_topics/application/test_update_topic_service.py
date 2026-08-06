"""Unit tests for `UpdateTopicService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import UpdateTopicInput
from app.modules.medical_topics.application.services.update_topic_service import (
    UpdateTopicService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic, TopicSpecialty
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.events import MedicalTopicUpdated
from app.modules.medical_topics.domain.exceptions import (
    CircularTopicHierarchyError,
    ParentTopicNotFoundError,
    TopicNotFoundError,
    TopicSpecialtyNotFoundError,
)
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicRepository,
    FakeTopicSpecialtyRepository,
    FakeUnitOfWork,
)


def _seeded() -> (
    tuple[
        UpdateTopicService, FakeMedicalTopicRepository, FakeTopicSpecialtyRepository, FakeUnitOfWork
    ]
):
    topics = FakeMedicalTopicRepository()
    specialties = FakeTopicSpecialtyRepository()
    uow = FakeUnitOfWork()
    service = UpdateTopicService(
        topic_repository=topics, specialty_repository=specialties, unit_of_work=uow
    )
    return service, topics, specialties, uow


async def _add_topic(topics: FakeMedicalTopicRepository, **overrides: object) -> MedicalTopic:
    defaults: dict[str, object] = {
        "slug": TopicSlug(f"topic-{uuid4().hex[:8]}"),
        "name": TopicName("Test Topic"),
    }
    defaults.update(overrides)
    topic = MedicalTopic.create(**defaults)  # type: ignore[arg-type]
    await topics.add(topic)
    return topic


class TestUpdateTopic:
    async def test_updates_the_name(self) -> None:
        service, topics, _, _ = _seeded()
        topic = await _add_topic(topics)
        await service.execute(UpdateTopicInput(topic_id=topic.id, name="Renamed"))
        stored = await topics.get_by_id(topic.id)
        assert stored is not None
        assert str(stored.name) == "Renamed"

    async def test_updates_status(self) -> None:
        service, topics, _, _ = _seeded()
        topic = await _add_topic(topics)
        await service.execute(UpdateTopicInput(topic_id=topic.id, status=TopicStatus.PUBLISHED))
        stored = await topics.get_by_id(topic.id)
        assert stored is not None
        assert stored.status is TopicStatus.PUBLISHED

    async def test_updates_visibility(self) -> None:
        service, topics, _, _ = _seeded()
        topic = await _add_topic(topics)
        await service.execute(
            UpdateTopicInput(topic_id=topic.id, visibility=TopicVisibility.PRIVATE)
        )
        stored = await topics.get_by_id(topic.id)
        assert stored is not None
        assert stored.visibility is TopicVisibility.PRIVATE

    async def test_unknown_topic_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(TopicNotFoundError):
            await service.execute(UpdateTopicInput(topic_id=uuid4(), name="X"))

    async def test_assigns_a_valid_parent(self) -> None:
        service, topics, _, _ = _seeded()
        parent = await _add_topic(topics)
        child = await _add_topic(topics)
        await service.execute(UpdateTopicInput(topic_id=child.id, parent_id=parent.id))
        stored = await topics.get_by_id(child.id)
        assert stored is not None
        assert stored.parent_id == parent.id

    async def test_unknown_parent_raises(self) -> None:
        service, topics, _, _ = _seeded()
        topic = await _add_topic(topics)
        with pytest.raises(ParentTopicNotFoundError):
            await service.execute(UpdateTopicInput(topic_id=topic.id, parent_id=uuid4()))

    async def test_direct_self_parent_raises_circular_hierarchy(self) -> None:
        """The service's own cycle walk (`_ensure_no_cycle`) catches this
        before ever reaching `MedicalTopic.update_profile`'s own, purely
        local `TopicCannotBeOwnParentError` check — self-as-parent is
        just a zero-hop cycle."""
        service, topics, _, _ = _seeded()
        topic = await _add_topic(topics)
        with pytest.raises(CircularTopicHierarchyError):
            await service.execute(UpdateTopicInput(topic_id=topic.id, parent_id=topic.id))

    async def test_assigning_a_descendant_as_parent_raises_circular_hierarchy(self) -> None:
        service, topics, _, _ = _seeded()
        grandparent = await _add_topic(topics)
        parent = await _add_topic(topics, parent_id=grandparent.id)
        child = await _add_topic(topics, parent_id=parent.id)

        with pytest.raises(CircularTopicHierarchyError):
            await service.execute(UpdateTopicInput(topic_id=grandparent.id, parent_id=child.id))

    async def test_clear_parent_removes_an_existing_parent(self) -> None:
        service, topics, _, _ = _seeded()
        parent = await _add_topic(topics)
        child = await _add_topic(topics, parent_id=parent.id)
        await service.execute(UpdateTopicInput(topic_id=child.id, clear_parent=True))
        stored = await topics.get_by_id(child.id)
        assert stored is not None
        assert stored.parent_id is None

    async def test_assigns_a_valid_specialty(self) -> None:
        service, topics, specialties, _ = _seeded()
        topic = await _add_topic(topics)
        specialty = TopicSpecialty.create(
            name=TopicName("Cardiology"), slug=TopicSlug("cardiology")
        )
        await specialties.add(specialty)

        await service.execute(UpdateTopicInput(topic_id=topic.id, specialty_id=specialty.id))
        stored = await topics.get_by_id(topic.id)
        assert stored is not None
        assert stored.specialty_id == specialty.id

    async def test_unknown_specialty_raises(self) -> None:
        service, topics, _, _ = _seeded()
        topic = await _add_topic(topics)
        with pytest.raises(TopicSpecialtyNotFoundError):
            await service.execute(UpdateTopicInput(topic_id=topic.id, specialty_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, topics, _, uow = _seeded()
        topic = await _add_topic(topics)
        await service.execute(UpdateTopicInput(topic_id=topic.id, name="X"))
        assert uow.committed is True

    async def test_publishes_a_medical_topic_updated_event(self) -> None:
        service, topics, _, uow = _seeded()
        topic = await _add_topic(topics)
        await service.execute(UpdateTopicInput(topic_id=topic.id, name="X"))
        assert any(isinstance(e, MedicalTopicUpdated) for e in uow.published_events)

    async def test_output_reflects_the_update(self) -> None:
        service, topics, _, _ = _seeded()
        topic = await _add_topic(topics)
        output = await service.execute(
            UpdateTopicInput(topic_id=topic.id, name="Renamed", visibility=TopicVisibility.UNLISTED)
        )
        assert output.topic_id == topic.id
        assert output.name == "Renamed"
        assert output.visibility is TopicVisibility.UNLISTED
