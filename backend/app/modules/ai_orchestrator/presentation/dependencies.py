"""FastAPI dependency wiring for the AI Healthcare Orchestrator module's
HTTP surface — mirrors every prior AI module's own
`presentation/dependencies.py` shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.ai_orchestrator.container import get_healthcare_orchestrator_facade
from app.modules.ai_orchestrator.public.facade import HealthcareOrchestratorFacade

HealthcareOrchestratorFacadeDep = Annotated[
    HealthcareOrchestratorFacade, Depends(get_healthcare_orchestrator_facade)
]
