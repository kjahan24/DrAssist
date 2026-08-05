"""The AI Risk Stratification & Early Warning Score module's public
port — the only contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.risk_stratification_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.risk_stratification_ai.public.dto import (
    GeneratedRiskStratification,
    RiskStratificationInput,
    RiskStratificationOutputFormat,
    RiskStratificationResult,
    RiskStratificationStreamChunk,
)


class RiskStratificationAIPort(ABC):
    @abstractmethod
    async def analyze_patient_risk(
        self, input_dto: RiskStratificationInput
    ) -> GeneratedRiskStratification: ...

    @abstractmethod
    def stream_analyze_patient_risk(
        self, input_dto: RiskStratificationInput
    ) -> AsyncIterator[RiskStratificationStreamChunk]: ...

    @abstractmethod
    async def render_result(
        self,
        result: RiskStratificationResult,
        *,
        target_format: RiskStratificationOutputFormat,
    ) -> str: ...
