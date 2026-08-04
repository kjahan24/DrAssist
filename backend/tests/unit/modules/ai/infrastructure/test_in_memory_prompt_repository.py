"""Unit tests for `InMemoryPromptTemplateRepository`."""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.ai.infrastructure.prompts.in_memory_repository import (
    InMemoryPromptTemplateRepository,
)


def _template(name: str = "greeting", version: int = 1) -> PromptTemplate:
    return PromptTemplate(name=name, version=version, template_string=f"v{version} of {name}")


class TestInMemoryPromptTemplateRepository:
    async def test_get_returns_none_when_absent(self) -> None:
        repo = InMemoryPromptTemplateRepository()
        assert await repo.get("greeting", 1) is None

    async def test_add_then_get_round_trips(self) -> None:
        repo = InMemoryPromptTemplateRepository()
        template = _template()
        await repo.add(template)
        assert await repo.get("greeting", 1) == template

    async def test_get_latest_returns_the_highest_version(self) -> None:
        repo = InMemoryPromptTemplateRepository()
        await repo.add(_template(version=1))
        await repo.add(_template(version=3))
        await repo.add(_template(version=2))

        latest = await repo.get_latest("greeting")

        assert latest is not None
        assert latest.version == 3

    async def test_get_latest_returns_none_for_unknown_name(self) -> None:
        repo = InMemoryPromptTemplateRepository()
        assert await repo.get_latest("never-registered") is None

    async def test_list_versions_is_sorted(self) -> None:
        repo = InMemoryPromptTemplateRepository()
        await repo.add(_template(version=2))
        await repo.add(_template(version=1))

        assert await repo.list_versions("greeting") == [1, 2]

    async def test_list_names_includes_every_registered_template(self) -> None:
        repo = InMemoryPromptTemplateRepository()
        await repo.add(_template(name="greeting"))
        await repo.add(_template(name="farewell"))

        assert await repo.list_names() == ["farewell", "greeting"]
