"""`ensure_risk_stratification_templates_registered` — idempotently
registers this module's 18 prompt templates (`templates.py`) into AI
Foundation's shared, process-lifetime `PromptRegistry`
(`app.modules.ai.container.get_prompt_registry`), the same pattern every
prior AI module's own `template_registrar.py` establishes for itself.

Not extracted into the shared kernel alongside `app.shared.infrastructure
.text_processing` — unlike that package's functions, this one needs AI
Foundation's own `PromptRegistry`/`PromptTemplate` types, and `app/shared/`
is never allowed to import from `app/modules/`. Each module that needs
this pattern therefore keeps its own small copy, parameterized only by
its own template list.
"""

import asyncio

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.risk_stratification_ai.infrastructure.prompts.templates import (
    build_all_templates,
)

_registration_lock = asyncio.Lock()
_templates_registered = False


async def ensure_risk_stratification_templates_registered(registry: PromptRegistry) -> None:
    global _templates_registered
    if _templates_registered:
        return
    async with _registration_lock:
        if _templates_registered:
            return
        for template in build_all_templates():
            await registry.register(template)
        _templates_registered = True
