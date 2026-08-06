"""Unit tests for `CreateTopicSpecialtyService`, using in-memory fakes."""

import pytest

from app.modules.medical_topics.application.dto import CreateTopicSpecialtyInput
from app.modules.medical_topics.application.services.create_topic_specialty_service import (
    CreateTopicSpecialtyService,
)
from app.modules.medical_topics.domain.events import TopicSpecialtyCreated
from app.modules.medical_topics.domain.exceptions import DuplicateTopicSpecialtyNameError
from tests.unit.modules.medical_topics.application.fakes import (
    FakeTopicSpecialtyRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[CreateTopicSpecialtyService, FakeTopicSpecialtyRepository, FakeUnitOfWork]:
    specialties = FakeTopicSpecialtyRepository()
    uow = FakeUnitOfWork()
    service = CreateTopicSpecialtyService(specialty_repository=specialties, unit_of_work=uow)
    return service, specialties, uow


class TestCreateTopicSpecialty:
    async def test_creates_a_specialty(self) -> None:
        service, specialties, _ = _seeded()
        output = await service.execute(CreateTopicSpecialtyInput(name="Oncology", slug="oncology"))
        stored = await specialties.get_by_id(output.specialty_id)
        assert stored is not None
        assert str(stored.name) == "Oncology"
        assert str(stored.slug) == "oncology"

    async def test_accepts_a_description(self) -> None:
        service, specialties, _ = _seeded()
        output = await service.execute(
            CreateTopicSpecialtyInput(name="Oncology", slug="oncology", description="Cancer care.")
        )
        stored = await specialties.get_by_id(output.specialty_id)
        assert stored is not None
        assert str(stored.description) == "Cancer care."

    async def test_new_specialty_defaults_to_active(self) -> None:
        service, specialties, _ = _seeded()
        output = await service.execute(CreateTopicSpecialtyInput(name="Oncology", slug="oncology"))
        stored = await specialties.get_by_id(output.specialty_id)
        assert stored is not None
        assert stored.is_active is True

    async def test_duplicate_name_raises(self) -> None:
        service, _, _ = _seeded()
        await service.execute(CreateTopicSpecialtyInput(name="Oncology", slug="oncology"))
        with pytest.raises(DuplicateTopicSpecialtyNameError):
            await service.execute(CreateTopicSpecialtyInput(name="Oncology", slug="oncology-2"))

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, uow = _seeded()
        await service.execute(CreateTopicSpecialtyInput(name="Oncology", slug="oncology"))
        assert uow.committed is True

    async def test_publishes_a_topic_specialty_created_event(self) -> None:
        service, _, uow = _seeded()
        await service.execute(CreateTopicSpecialtyInput(name="Oncology", slug="oncology"))
        assert any(isinstance(e, TopicSpecialtyCreated) for e in uow.published_events)

    async def test_output_reflects_the_created_specialty(self) -> None:
        service, _, _ = _seeded()
        output = await service.execute(CreateTopicSpecialtyInput(name="Oncology", slug="oncology"))
        assert output.name == "Oncology"
        assert output.slug == "oncology"
