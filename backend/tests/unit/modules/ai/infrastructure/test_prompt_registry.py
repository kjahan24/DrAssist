"""Unit tests for `PromptRegistry`."""

import pytest

from app.modules.ai.application.dto import PromptVariables
from app.modules.ai.domain.exceptions import (
    DuplicatePromptTemplateVersionError,
    PromptTemplateNotFoundError,
)
from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.ai.infrastructure.prompts.in_memory_repository import (
    InMemoryPromptTemplateRepository,
)
from app.modules.ai.infrastructure.prompts.registry import PromptRegistry


def _registry() -> PromptRegistry:
    return PromptRegistry(repository=InMemoryPromptTemplateRepository())


def _template(version: int = 1, template_string: str = "Hello {{ name }}!") -> PromptTemplate:
    return PromptTemplate(name="greeting", version=version, template_string=template_string)


class TestRegister:
    async def test_registers_a_new_template(self) -> None:
        registry = _registry()
        await registry.register(_template())
        assert await registry.get("greeting", version=1) == _template()

    async def test_rejects_a_duplicate_name_and_version(self) -> None:
        registry = _registry()
        await registry.register(_template())
        with pytest.raises(DuplicatePromptTemplateVersionError):
            await registry.register(_template())

    async def test_allows_a_new_version_of_an_existing_name(self) -> None:
        registry = _registry()
        await registry.register(_template(version=1))
        await registry.register(_template(version=2, template_string="Hi {{ name }}!"))
        assert await registry.list_versions("greeting") == [1, 2]


class TestGet:
    async def test_get_without_version_returns_latest(self) -> None:
        registry = _registry()
        await registry.register(_template(version=1))
        await registry.register(_template(version=2, template_string="v2 {{ name }}"))

        latest = await registry.get("greeting")

        assert latest.version == 2

    async def test_get_raises_when_name_unknown(self) -> None:
        registry = _registry()
        with pytest.raises(PromptTemplateNotFoundError):
            await registry.get("never-registered")

    async def test_get_raises_when_version_unknown(self) -> None:
        registry = _registry()
        await registry.register(_template(version=1))
        with pytest.raises(PromptTemplateNotFoundError):
            await registry.get("greeting", version=99)


class TestRender:
    async def test_renders_the_latest_version_by_default(self) -> None:
        registry = _registry()
        await registry.register(_template())

        rendered = await registry.render("greeting", PromptVariables({"name": "Ada"}))

        assert rendered == "Hello Ada!"

    async def test_renders_a_specific_pinned_version(self) -> None:
        registry = _registry()
        await registry.register(_template(version=1, template_string="v1 says hi to {{ name }}"))
        await registry.register(_template(version=2, template_string="v2 says hi to {{ name }}"))

        rendered = await registry.render("greeting", PromptVariables({"name": "Ada"}), version=1)

        assert rendered == "v1 says hi to Ada"
