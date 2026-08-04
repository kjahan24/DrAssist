"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, so there
is exactly one definition of each shape (the same "re-exported... not
redefined" precedent `app.modules.family_access.public.dto` and
`app.modules.ai.public.dto` both establish). `ClinicalContext` is
deliberately **not** re-exported here — it is an internal orchestration
detail of `ClinicalCopilotService`, never a shape a caller constructs or
receives; only the request/response envelope is public.
"""

from app.modules.ai_copilot.application.dto import AIResponse
from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.value_objects import AIRequest, AISession

__all__ = ["AIRequest", "AIResponse", "AISession", "CopilotOutputFormat"]
