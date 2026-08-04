"""`InMemoryPromptTemplateRepository` — the concrete
`PromptTemplateRepository` this task ships. No `prompt_templates` table
exists yet (see `domain/repositories.py`'s own docstring for why), so
templates registered at process startup (`container.py::
build_prompt_registry`) live for the lifetime of the process only —
acceptable for a Foundation-layer task with no prompt-authoring UI yet;
swapping in a DB-backed implementation later requires no change to
`PromptRegistry`, which depends only on the abstract interface.
"""

from app.modules.ai.domain.repositories import PromptTemplateRepository
from app.modules.ai.domain.value_objects import PromptTemplate


class InMemoryPromptTemplateRepository(PromptTemplateRepository):
    def __init__(self) -> None:
        self._templates: dict[str, dict[int, PromptTemplate]] = {}

    async def get(self, name: str, version: int) -> PromptTemplate | None:
        return self._templates.get(name, {}).get(version)

    async def get_latest(self, name: str) -> PromptTemplate | None:
        versions = self._templates.get(name)
        if not versions:
            return None
        return versions[max(versions)]

    async def list_versions(self, name: str) -> list[int]:
        return sorted(self._templates.get(name, {}).keys())

    async def list_names(self) -> list[str]:
        return sorted(self._templates.keys())

    async def add(self, template: PromptTemplate) -> None:
        self._templates.setdefault(template.name, {})[template.version] = template
