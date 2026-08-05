"""FastAPI dependency wiring for the AI Patient Education & Discharge
Instructions module's HTTP surface — mirrors every prior AI module's
own `presentation/dependencies.py` shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.patient_education_ai.container import get_patient_education_ai_facade
from app.modules.patient_education_ai.public.facade import PatientEducationAIFacade

PatientEducationAIFacadeDep = Annotated[
    PatientEducationAIFacade, Depends(get_patient_education_ai_facade)
]
