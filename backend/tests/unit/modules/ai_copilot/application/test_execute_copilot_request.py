"""Unit tests for the `ExecuteCopilotRequest` use case."""

from uuid import uuid4

import pytest

from app.modules.ai.public.dto import AIModel, AIProviderType
from app.modules.ai_copilot.application.services.clinical_copilot_service import (
    ClinicalCopilotService,
)
from app.modules.ai_copilot.application.services.context_builder import ContextBuilder
from app.modules.ai_copilot.application.services.prompt_builder import PromptBuilder
from app.modules.ai_copilot.application.use_cases.execute_copilot_request import (
    ExecuteCopilotRequest,
)
from app.modules.ai_copilot.domain.exceptions import PatientNotFoundError
from app.modules.ai_copilot.domain.value_objects import AIRequest
from tests.unit.modules.ai_copilot.application.fakes import (
    FakeAIGateway,
    FakeAIResponseValidator,
    FakeClinicalNoteQueryPort,
    FakeCopilotAuditLogger,
    FakeCopilotOutputParser,
    FakeCostEstimator,
    FakeLabResultQueryPort,
    FakePatientQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    FakeTimelineQueryPort,
    FakeVisitQueryPort,
    make_patient_summary,
)


def _use_case(patients: FakePatientQueryPort) -> ExecuteCopilotRequest:
    context_builder = ContextBuilder(
        patient_query_port=patients,
        prescription_query_port=FakePrescriptionQueryPort(),
        visit_query_port=FakeVisitQueryPort(),
        clinical_note_query_port=FakeClinicalNoteQueryPort(),
        soap_note_query_port=FakeSOAPNoteQueryPort(),
        lab_result_query_port=FakeLabResultQueryPort(),
        timeline_query_port=FakeTimelineQueryPort(),
    )
    gateway = FakeAIGateway()
    service = ClinicalCopilotService(
        context_builder=context_builder,
        prompt_builder=PromptBuilder(ai_gateway=gateway),
        ai_gateway=gateway,
        output_parser=FakeCopilotOutputParser(),
        response_validator=FakeAIResponseValidator(),
        audit_logger=FakeCopilotAuditLogger(),
        cost_estimator=FakeCostEstimator(),
        default_model=AIModel(provider=AIProviderType.MOCK, name="mock-model"),
    )
    return ExecuteCopilotRequest(service=service)


class TestExecuteCopilotRequest:
    async def test_delegates_to_the_service(self) -> None:
        patient_id = uuid4()
        patients = FakePatientQueryPort()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        use_case = _use_case(patients)

        response = await use_case.execute(
            AIRequest(request_type="generic", patient_id=patient_id, prompt_version=1)
        )

        assert response.session is not None

    async def test_propagates_service_errors(self) -> None:
        use_case = _use_case(FakePatientQueryPort())

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(
                AIRequest(request_type="generic", patient_id=uuid4(), prompt_version=1)
            )
