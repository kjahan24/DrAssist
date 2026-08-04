"""Unit tests for `ensure_lab_interpretation_templates_registered` —
including the idempotency guarantee (repeated calls, and concurrent
calls, must register each template exactly once)."""

import asyncio
from collections.abc import Iterator

import pytest

import app.modules.lab_interpretation_ai.infrastructure.prompts.template_registrar as registrar_module  # noqa: E501
from app.modules.ai.infrastructure.prompts.in_memory_repository import (
    InMemoryPromptTemplateRepository,
)
from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.lab_interpretation_ai.infrastructure.prompts.template_registrar import (
    ensure_lab_interpretation_templates_registered,
)


@pytest.fixture(autouse=True)
def _reset_registration_flag() -> Iterator[None]:
    registrar_module._templates_registered = False
    yield
    registrar_module._templates_registered = False


def _registry() -> PromptRegistry:
    return PromptRegistry(repository=InMemoryPromptTemplateRepository())


class TestEnsureLabInterpretationTemplatesRegistered:
    async def test_registers_all_fifteen_templates(self) -> None:
        registry = _registry()

        await ensure_lab_interpretation_templates_registered(registry)

        assert len(await registry.list_names()) == 15

    async def test_calling_twice_does_not_raise(self) -> None:
        registry = _registry()

        await ensure_lab_interpretation_templates_registered(registry)
        await ensure_lab_interpretation_templates_registered(registry)

    async def test_calling_twice_does_not_register_duplicates(self) -> None:
        registry = _registry()

        await ensure_lab_interpretation_templates_registered(registry)
        await ensure_lab_interpretation_templates_registered(registry)

        assert len(await registry.list_names()) == 15

    async def test_concurrent_calls_register_exactly_once(self) -> None:
        registry = _registry()

        await asyncio.gather(
            *(ensure_lab_interpretation_templates_registered(registry) for _ in range(5))
        )

        assert len(await registry.list_names()) == 15

    async def test_registered_templates_are_renderable(self) -> None:
        from app.modules.ai.application.dto import PromptVariables

        registry = _registry()
        await ensure_lab_interpretation_templates_registered(registry)

        rendered = await registry.render(
            "lab_interpretation.outpatient.system", PromptVariables({"language": "en"}), version=1
        )

        assert "en" in rendered
