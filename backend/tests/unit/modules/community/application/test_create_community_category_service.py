"""Unit tests for `CreateCommunityCategoryService`, using in-memory fakes."""

import pytest

from app.modules.community.application.dto import CreateCommunityCategoryInput
from app.modules.community.application.services.create_community_category_service import (
    CreateCommunityCategoryService,
)
from app.modules.community.domain.events import CommunityCategoryCreated
from app.modules.community.domain.exceptions import DuplicateCommunityCategoryNameError
from tests.unit.modules.community.application.fakes import (
    FakeCommunityCategoryRepository,
    FakeUnitOfWork,
)


def _seeded() -> (
    tuple[CreateCommunityCategoryService, FakeCommunityCategoryRepository, FakeUnitOfWork]
):
    categories = FakeCommunityCategoryRepository()
    uow = FakeUnitOfWork()
    service = CreateCommunityCategoryService(
        community_category_repository=categories, unit_of_work=uow
    )
    return service, categories, uow


class TestCreateCommunityCategory:
    async def test_creates_a_category(self) -> None:
        service, categories, _ = _seeded()
        output = await service.execute(
            CreateCommunityCategoryInput(name="Oncology", slug="oncology")
        )
        stored = await categories.get_by_id(output.category_id)
        assert stored is not None
        assert str(stored.name) == "Oncology"
        assert str(stored.slug) == "oncology"

    async def test_accepts_a_description(self) -> None:
        service, categories, _ = _seeded()
        output = await service.execute(
            CreateCommunityCategoryInput(
                name="Oncology", slug="oncology", description="Cancer care."
            )
        )
        stored = await categories.get_by_id(output.category_id)
        assert stored is not None
        assert stored.description == "Cancer care."

    async def test_new_category_defaults_to_active(self) -> None:
        service, categories, _ = _seeded()
        output = await service.execute(
            CreateCommunityCategoryInput(name="Oncology", slug="oncology")
        )
        stored = await categories.get_by_id(output.category_id)
        assert stored is not None
        assert stored.is_active is True

    async def test_duplicate_name_raises(self) -> None:
        service, _, _ = _seeded()
        await service.execute(CreateCommunityCategoryInput(name="Oncology", slug="oncology"))
        with pytest.raises(DuplicateCommunityCategoryNameError):
            await service.execute(CreateCommunityCategoryInput(name="Oncology", slug="oncology-2"))

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, uow = _seeded()
        await service.execute(CreateCommunityCategoryInput(name="Oncology", slug="oncology"))
        assert uow.committed is True

    async def test_publishes_a_community_category_created_event(self) -> None:
        service, _, uow = _seeded()
        await service.execute(CreateCommunityCategoryInput(name="Oncology", slug="oncology"))
        assert any(isinstance(e, CommunityCategoryCreated) for e in uow.published_events)

    async def test_output_reflects_the_created_category(self) -> None:
        service, _, _ = _seeded()
        output = await service.execute(
            CreateCommunityCategoryInput(name="Oncology", slug="oncology")
        )
        assert output.name == "Oncology"
        assert output.slug == "oncology"
