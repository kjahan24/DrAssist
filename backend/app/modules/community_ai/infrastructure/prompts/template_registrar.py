"""`ensure_community_ai_templates_registered` — idempotently registers
this module's 6 prompt templates (`templates.py`) into AI Foundation's
shared, process-lifetime `PromptRegistry`
(`app.modules.ai.container.get_prompt_registry`), the identical
lock+flag-guarded pattern
`app.modules.icd10_ai.infrastructure.prompts.template_registrar
.ensure_icd10_templates_registered` establishes for itself — see that
module's own docstring for the full reasoning."""

import asyncio

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.community_ai.infrastructure.prompts.templates import build_all_templates

_registration_lock = asyncio.Lock()
_templates_registered = False


async def ensure_community_ai_templates_registered(registry: PromptRegistry) -> None:
    global _templates_registered
    if _templates_registered:
        return
    async with _registration_lock:
        if _templates_registered:
            return
        for template in build_all_templates():
            await registry.register(template)
        _templates_registered = True
