"""FastAPI dependency wiring for the AI Medical Reasoning Engine's HTTP
surface — mirrors `app.modules.differential_diagnosis_ai.presentation
.dependencies`'s own shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.medical_reasoning_ai.container import get_medical_reasoning_ai_facade
from app.modules.medical_reasoning_ai.public.facade import MedicalReasoningAIFacade

MedicalReasoningAIFacadeDep = Annotated[
    MedicalReasoningAIFacade, Depends(get_medical_reasoning_ai_facade)
]
