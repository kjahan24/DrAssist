"""FastAPI dependency wiring for the AI Lab Interpretation module's HTTP
surface — mirrors every prior AI module's own `presentation
/dependencies.py` shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.lab_interpretation_ai.container import get_lab_interpretation_ai_facade
from app.modules.lab_interpretation_ai.public.facade import LabInterpretationAIFacade

LabInterpretationAIFacadeDep = Annotated[
    LabInterpretationAIFacade, Depends(get_lab_interpretation_ai_facade)
]
