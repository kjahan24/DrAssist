"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them — the same "exactly one definition of each shape"
guarantee `app.modules.family_access.public.dto` and
`app.modules.ai.public.dto` both establish for their own modules."""

from app.modules.ai_copilot.application.dto import AIResponse as ApplicationAIResponse
from app.modules.ai_copilot.domain.enums import CopilotOutputFormat as DomainCopilotOutputFormat
from app.modules.ai_copilot.domain.value_objects import AIRequest as DomainAIRequest
from app.modules.ai_copilot.domain.value_objects import AISession as DomainAISession
from app.modules.ai_copilot.public.dto import AIRequest, AIResponse, AISession, CopilotOutputFormat


class TestPublicDtoReExports:
    def test_ai_request_is_the_same_type_as_the_domain_value_object(self) -> None:
        assert AIRequest is DomainAIRequest

    def test_ai_session_is_the_same_type_as_the_domain_value_object(self) -> None:
        assert AISession is DomainAISession

    def test_ai_response_is_the_same_type_as_the_application_dto(self) -> None:
        assert AIResponse is ApplicationAIResponse

    def test_copilot_output_format_is_the_same_type_as_the_domain_enum(self) -> None:
        assert CopilotOutputFormat is DomainCopilotOutputFormat
