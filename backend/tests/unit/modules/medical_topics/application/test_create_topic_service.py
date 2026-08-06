"""Unit tests for `CreateTopicService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.medical_topics.application.dto import CreateTopicInput
from app.modules.medical_topics.application.services.create_topic_service import (
    CreateTopicService,
)
from app.modules.medical_topics.domain.entities import MedicalTopic, TopicSpecialty
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.events import MedicalTopicCreated
from app.modules.medical_topics.domain.exceptions import (
    DuplicateTopicSlugError,
    ParentTopicNotFoundError,
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
        CreateTopicService, FakeMedicalTopicRepository, FakeTopicSpecialtyRepository, FakeUnitOfWork
    ]
):
    topics = FakeMedicalTopicRepository()
    specialties = FakeTopicSpecialtyRepository()
    uow = FakeUnitOfWork()
    service = CreateTopicService(
        topic_repository=topics, specialty_repository=specialties, unit_of_work=uow
    )
    return service, topics, specialties, uow


class TestCreateTopic:
    async def test_creates_a_topic(self) -> None:
        service, topics, _, _ = _seeded()
        output = await service.execute(
            CreateTopicInput(slug="cardiac-arrhythmia", name="Cardiac Arrhythmia")
        )
        stored = await topics.get_by_id(output.topic_id)
        assert stored is not None
        assert str(stored.name) == "Cardiac Arrhythmia"
        assert str(stored.slug) == "cardiac-arrhythmia"

    async def test_new_topic_defaults_to_draft_status(self) -> None:
        service, _, _, _ = _seeded()
        output = await service.execute(
            CreateTopicInput(slug="cardiac-arrhythmia", name="Cardiac Arrhythmia")
        )
        assert output.status is TopicStatus.DRAFT

    async def test_accepts_explicit_visibility(self) -> None:
        service, _, _, _ = _seeded()
        output = await service.execute(
            CreateTopicInput(
                slug="cardiac-arrhythmia",
                name="Cardiac Arrhythmia",
                visibility=TopicVisibility.UNLISTED,
            )
        )
        assert output.visibility is TopicVisibility.UNLISTED

    async def test_accepts_description_icon_and_color(self) -> None:
        service, topics, _, _ = _seeded()
        output = await service.execute(
            CreateTopicInput(
                slug="cardiac-arrhythmia",
                name="Cardiac Arrhythmia",
                description="Covers irregular heart rhythms.",
                icon="heart-pulse",
                color="#FF5733",
            )
        )
        stored = await topics.get_by_id(output.topic_id)
        assert stored is not None
        assert str(stored.description) == "Covers irregular heart rhythms."
        assert stored.icon == "heart-pulse"
        assert str(stored.color) == "#FF5733"

    async def test_duplicate_slug_raises(self) -> None:
        service, _, _, _ = _seeded()
        await service.execute(CreateTopicInput(slug="oncology", name="Oncology"))
        with pytest.raises(DuplicateTopicSlugError):
            await service.execute(CreateTopicInput(slug="oncology", name="Oncology Two"))

    async def test_accepts_a_valid_parent(self) -> None:
        service, topics, _, _ = _seeded()
        parent = MedicalTopic.create(slug=TopicSlug("cardiology"), name=TopicName("Cardiology"))
        await topics.add(parent)

        output = await service.execute(
            CreateTopicInput(
                slug="cardiac-arrhythmia", name="Cardiac Arrhythmia", parent_id=parent.id
            )
        )
        stored = await topics.get_by_id(output.topic_id)
        assert stored is not None
        assert stored.parent_id == parent.id

    async def test_unknown_parent_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(ParentTopicNotFoundError):
            await service.execute(
                CreateTopicInput(
                    slug="cardiac-arrhythmia", name="Cardiac Arrhythmia", parent_id=uuid4()
                )
            )

    async def test_accepts_a_valid_specialty(self) -> None:
        service, topics, specialties, _ = _seeded()
        specialty = TopicSpecialty.create(
            name=TopicName("Cardiology"), slug=TopicSlug("cardiology")
        )
        await specialties.add(specialty)

        output = await service.execute(
            CreateTopicInput(
                slug="cardiac-arrhythmia", name="Cardiac Arrhythmia", specialty_id=specialty.id
            )
        )
        stored = await topics.get_by_id(output.topic_id)
        assert stored is not None
        assert stored.specialty_id == specialty.id

    async def test_unknown_specialty_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(TopicSpecialtyNotFoundError):
            await service.execute(
                CreateTopicInput(
                    slug="cardiac-arrhythmia", name="Cardiac Arrhythmia", specialty_id=uuid4()
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, _, uow = _seeded()
        await service.execute(CreateTopicInput(slug="oncology", name="Oncology"))
        assert uow.committed is True

    async def test_publishes_a_medical_topic_created_event(self) -> None:
        service, _, _, uow = _seeded()
        await service.execute(CreateTopicInput(slug="oncology", name="Oncology"))
        assert any(isinstance(e, MedicalTopicCreated) for e in uow.published_events)

    async def test_output_reflects_the_created_topic(self) -> None:
        service, _, _, _ = _seeded()
        output = await service.execute(CreateTopicInput(slug="oncology", name="Oncology"))
        assert output.slug == "oncology"
        assert output.name == "Oncology"
