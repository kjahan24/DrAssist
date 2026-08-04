"""`ExecuteCopilotRequest` — the `UseCase`-shaped entry point
`public/facade.py::ClinicalCopilotFacade` wraps, matching the
`UseCase[TInput, TOutput]` shape every other module's own use cases
extend (`app.shared.application.use_case`). Deliberately thin: the real
8-stage pipeline lives in `ClinicalCopilotService`, per that class's own
docstring — this wrapper exists only so this module's public entry point
has the same recognizable shape as every other module's, the same
`GenerateChatCompletion`/`GenerateEmbedding` precedent AI Foundation
itself establishes for a service-backed use case.
"""

from app.modules.ai_copilot.application.dto import AIResponse
from app.modules.ai_copilot.application.services.clinical_copilot_service import (
    ClinicalCopilotService,
)
from app.modules.ai_copilot.domain.value_objects import AIRequest
from app.shared.application.use_case import UseCase


class ExecuteCopilotRequest(UseCase[AIRequest, AIResponse]):
    def __init__(self, *, service: ClinicalCopilotService) -> None:
        self._service = service

    async def execute(self, input_dto: AIRequest) -> AIResponse:
        return await self._service.execute(input_dto)
