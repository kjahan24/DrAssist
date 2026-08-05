"""FastAPI dependency wiring for the AI Drug Interaction & Medication
Safety module's HTTP surface — mirrors every prior AI module's own
`presentation/dependencies.py` shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.drug_interaction_ai.container import get_drug_interaction_ai_facade
from app.modules.drug_interaction_ai.public.facade import DrugInteractionAIFacade

DrugInteractionAIFacadeDep = Annotated[
    DrugInteractionAIFacade, Depends(get_drug_interaction_ai_facade)
]
