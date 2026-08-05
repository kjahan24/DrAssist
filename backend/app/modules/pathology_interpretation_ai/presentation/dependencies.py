"""FastAPI dependency wiring for the AI Pathology Interpretation
module's HTTP surface — mirrors every prior AI module's own
`presentation/dependencies.py` shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.pathology_interpretation_ai.container import (
    get_pathology_interpretation_ai_facade,
)
from app.modules.pathology_interpretation_ai.public.facade import (
    PathologyInterpretationAIFacade,
)

PathologyInterpretationAIFacadeDep = Annotated[
    PathologyInterpretationAIFacade, Depends(get_pathology_interpretation_ai_facade)
]
