"""`PromptRegistry` — the versioned prompt store other code registers
templates into and resolves/renders them from.

A thin orchestrator over `domain/repositories.py::PromptTemplateRepository`
+ `PromptRenderer` — it owns no storage of its own (that's the injected
repository's job, `infrastructure/prompts/in_memory_repository.py` for
this task), matching the Repository Pattern's usual split between "where
data lives" and "what you do with it" (`04_repository_and_service_patterns
.md`).
"""

from app.modules.ai.application.dto import PromptVariables
from app.modules.ai.domain.exceptions import (
    DuplicatePromptTemplateVersionError,
    PromptTemplateNotFoundError,
)
from app.modules.ai.domain.repositories import PromptTemplateRepository
from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.ai.infrastructure.prompts.renderer import PromptRenderer


class PromptRegistry:
    def __init__(
        self, *, repository: PromptTemplateRepository, renderer: PromptRenderer | None = None
    ) -> None:
        self._repository = repository
        self._renderer = renderer or PromptRenderer()

    async def register(self, template: PromptTemplate) -> None:
        existing = await self._repository.get(template.name, template.version)
        if existing is not None:
            raise DuplicatePromptTemplateVersionError(template.name, template.version)
        await self._repository.add(template)

    async def get(self, name: str, *, version: int | None = None) -> PromptTemplate:
        template = (
            await self._repository.get(name, version)
            if version is not None
            else await self._repository.get_latest(name)
        )
        if template is None:
            raise PromptTemplateNotFoundError(name, version)
        return template

    async def list_versions(self, name: str) -> list[int]:
        return await self._repository.list_versions(name)

    async def list_names(self) -> list[str]:
        return await self._repository.list_names()

    async def render(
        self, name: str, variables: PromptVariables, *, version: int | None = None
    ) -> str:
        template = await self.get(name, version=version)
        return self._renderer.render(template, variables)
