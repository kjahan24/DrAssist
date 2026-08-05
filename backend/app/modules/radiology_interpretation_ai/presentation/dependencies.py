"""FastAPI dependency wiring for the AI Radiology Interpretation
module's HTTP surface — mirrors every prior AI module's own
`presentation/dependencies.py` shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.radiology_interpretation_ai.container import (
    get_radiology_interpretation_ai_facade,
)
from app.modules.radiology_interpretation_ai.public.facade import RadiologyInterpretationAIFacade

RadiologyInterpretationAIFacadeDep = Annotated[
    RadiologyInterpretationAIFacade, Depends(get_radiology_interpretation_ai_facade)
]
