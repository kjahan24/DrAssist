"""`ClinicalCopilotFacade` — the one concrete implementation of
`ClinicalCopilotPort`. Constructed by
`app.modules.ai_copilot.container.build_clinical_copilot_facade`.
"""

from app.modules.ai_copilot.application.use_cases.execute_copilot_request import (
    ExecuteCopilotRequest,
)
from app.modules.ai_copilot.public.dto import AIRequest, AIResponse
from app.modules.ai_copilot.public.interfaces import ClinicalCopilotPort


class ClinicalCopilotFacade(ClinicalCopilotPort):
    def __init__(self, *, execute_use_case: ExecuteCopilotRequest) -> None:
        self._execute_use_case = execute_use_case

    async def execute(self, request: AIRequest) -> AIResponse:
        return await self._execute_use_case.execute(request)
