"""Unit tests for the AI Clinical Copilot module's application DTOs."""

from uuid import uuid4

from app.modules.ai_copilot.application.dto import AIResponse, ClinicalContext
from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.value_objects import AISession
from tests.unit.modules.ai_copilot.application.fakes import make_patient_summary


class TestClinicalContext:
    def test_constructs_with_all_sections(self) -> None:
        context = ClinicalContext(
            patient=make_patient_summary(),
            allergies=(),
            medications=(),
            conditions=(),
            visits=(),
            clinical_notes=(),
            soap_notes=(),
            lab_results=(),
            timeline_events=(),
        )
        assert context.allergies == ()


class TestAIResponse:
    def test_request_id_aliases_the_session_request_id(self) -> None:
        request_id = uuid4()
        session = AISession(
            request_id=request_id,
            provider="mock",
            model="mock-model",
            prompt_name="generic",
            prompt_version=1,
            latency_ms=1.0,
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            estimated_cost_usd=0.0,
        )
        response = AIResponse(
            output_format=CopilotOutputFormat.JSON,
            raw_text="{}",
            parsed_content={},
            session=session,
        )
        assert response.request_id == request_id
