"""FastAPI dependency wiring for the AI Differential Diagnosis module's
HTTP surface — mirrors `app.modules.prescription_ai.presentation
.dependencies`'s own shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.differential_diagnosis_ai.container import get_differential_diagnosis_ai_facade
from app.modules.differential_diagnosis_ai.public.facade import DifferentialDiagnosisAIFacade

DifferentialDiagnosisAIFacadeDep = Annotated[
    DifferentialDiagnosisAIFacade, Depends(get_differential_diagnosis_ai_facade)
]
