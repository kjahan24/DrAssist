"""FastAPI dependency wiring for the AI Risk Stratification & Early
Warning Score module's HTTP surface — mirrors every prior AI module's
own `presentation/dependencies.py` shape."""

from typing import Annotated

from fastapi import Depends

from app.modules.risk_stratification_ai.container import get_risk_stratification_ai_facade
from app.modules.risk_stratification_ai.public.facade import RiskStratificationAIFacade

RiskStratificationAIFacadeDep = Annotated[
    RiskStratificationAIFacade, Depends(get_risk_stratification_ai_facade)
]
