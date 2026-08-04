"""Repository interface for `PromptTemplate`, expressed in domain
vocabulary only. Concrete implementation for this task is
`infrastructure/prompts/in_memory_repository.py::InMemoryPromptTemplateRepository`
— no `prompt_templates` table exists yet, so templates are registered in
code at process startup (`container.py::build_prompt_registry`); a future
DB-backed implementation (letting non-engineers edit prompts without a
deploy) can implement this same interface with zero change to
`infrastructure/prompts/registry.py::PromptRegistry`, which depends only
on this abstraction.
"""

from abc import ABC, abstractmethod

from app.modules.ai.domain.value_objects import PromptTemplate


class PromptTemplateRepository(ABC):
    @abstractmethod
    async def get(self, name: str, version: int) -> PromptTemplate | None: ...

    @abstractmethod
    async def get_latest(self, name: str) -> PromptTemplate | None: ...

    @abstractmethod
    async def list_versions(self, name: str) -> list[int]: ...

    @abstractmethod
    async def list_names(self) -> list[str]: ...

    @abstractmethod
    async def add(self, template: PromptTemplate) -> None: ...
