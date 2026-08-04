"""FastAPI dependency wiring for the AI Prescription Assistance module's
HTTP surface — mirrors `app.modules.icd10_ai.presentation.dependencies`'s
own shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.prescription_ai.container import get_prescription_ai_facade
from app.modules.prescription_ai.public.facade import PrescriptionAIFacade

PrescriptionAIFacadeDep = Annotated[PrescriptionAIFacade, Depends(get_prescription_ai_facade)]
