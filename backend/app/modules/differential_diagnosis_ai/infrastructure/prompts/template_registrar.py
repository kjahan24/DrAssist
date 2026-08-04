"""`ensure_differential_diagnosis_templates_registered` — idempotently
registers this module's 15 prompt templates (`templates.py`) into AI
Foundation's shared, process-lifetime `PromptRegistry`
(`app.modules.ai.container.get_prompt_registry`), the same pattern
`app.modules.prescription_ai.infrastructure.prompts.template_registrar
.ensure_prescription_templates_registered` establishes for its own
module (see that module's own docstring for the full reasoning: why this
happens lazily rather than via an `app/main.py` startup hook, and why the
lock+flag guard exists).

Not extracted into the shared kernel alongside `app.shared.infrastructure
.text_processing` — unlike that package's functions, this one needs AI
Foundation's own `PromptRegistry`/`PromptTemplate` types, and `app/shared/`
is never allowed to import from `app/modules/`
(`docs/backend-architecture/11_standards_and_conventions.md`). Each
module that needs this pattern therefore keeps its own small copy,
parameterized only by its own template list — genuinely sharing it would
require either violating that layering rule or adding a third composition
mechanism for one nine-line function, which is not a worthwhile trade.
"""

import asyncio

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.differential_diagnosis_ai.infrastructure.prompts.templates import (
    build_all_templates,
)

_registration_lock = asyncio.Lock()
_templates_registered = False


async def ensure_differential_diagnosis_templates_registered(registry: PromptRegistry) -> None:
    global _templates_registered
    if _templates_registered:
        return
    async with _registration_lock:
        if _templates_registered:
            return
        for template in build_all_templates():
            await registry.register(template)
        _templates_registered = True
