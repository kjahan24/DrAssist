"""FastAPI dependency wiring for the AI ICD-10 Coding module's HTTP
surface — mirrors `app.modules.soap_note_ai.presentation.dependencies`'s
own shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.icd10_ai.container import get_icd10_ai_facade
from app.modules.icd10_ai.public.facade import ICD10AIFacade

ICD10AIFacadeDep = Annotated[ICD10AIFacade, Depends(get_icd10_ai_facade)]
