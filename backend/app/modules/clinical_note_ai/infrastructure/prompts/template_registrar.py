"""`ensure_clinical_note_templates_registered` — idempotently registers
this module's 15 prompt templates (`templates.py`) into AI Foundation's
shared, process-lifetime `PromptRegistry`
(`app.modules.ai.container.get_prompt_registry`).

Called lazily, on first real generation call
(`infrastructure/generation/clinical_note_generator.py`), rather than at
import time — `PromptRegistry.register()` is `async`, and this module
otherwise avoids requiring an explicit app-startup hook (e.g. a new line
in `app/main.py`'s `lifespan`) just to wire itself in, matching the
"never modify completed backend modules unless strictly required for
dependency injection" rule as narrowly as possible: nothing outside this
module's own files changes. An `asyncio.Lock` plus a module-level flag
guard against two concurrent requests both attempting registration
before either finishes (`PromptRegistry.register` raises
`DuplicatePromptTemplateVersionError`, from AI Foundation's `.domain`, on
a second attempt at the same name+version — a real, if unlikely, race
this guards against rather than letting propagate as a confusing
first-request-of-the-process error).
"""

import asyncio

from app.modules.ai.infrastructure.prompts.registry import PromptRegistry
from app.modules.clinical_note_ai.infrastructure.prompts.templates import build_all_templates

_registration_lock = asyncio.Lock()
_templates_registered = False


async def ensure_clinical_note_templates_registered(registry: PromptRegistry) -> None:
    global _templates_registered
    if _templates_registered:
        return
    async with _registration_lock:
        if _templates_registered:
            return
        for template in build_all_templates():
            await registry.register(template)
        _templates_registered = True
