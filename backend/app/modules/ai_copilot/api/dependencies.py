"""FastAPI dependency providers for the AI Clinical Copilot module.

`get_clinical_copilot_facade` is provided now, ahead of any real endpoint
using it, so the first clinical-feature module to build a genuine
authenticated route can `Depends()` on it immediately rather than
reinventing this wiring — the same "structure only" pattern this
codebase already uses (`app.modules.family_access.container`'s own scope
note describes an identical situation for RBAC dependencies it reuses
as-is rather than rebuilding).
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.modules.ai_copilot.container import build_clinical_copilot_facade
from app.modules.ai_copilot.public.facade import ClinicalCopilotFacade


async def get_clinical_copilot_facade(session: DbSession) -> ClinicalCopilotFacade:
    return build_clinical_copilot_facade(session)


ClinicalCopilotFacadeDep = Annotated[ClinicalCopilotFacade, Depends(get_clinical_copilot_facade)]
