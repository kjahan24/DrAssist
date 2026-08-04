"""Unit tests for `ClinicalCopilotFacade` — exercised through
`ClinicalCopilotPort` exactly as a future clinical-feature module would
call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract tests"
framing."""

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
from app.modules.ai_copilot.public.dto import AIRequest
from app.modules.ai_copilot.public.facade import ClinicalCopilotFacade
from app.modules.ai_copilot.public.interfaces import ClinicalCopilotPort
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


def _facade(patients: FakePatientQueryPort) -> ClinicalCopilotFacade:
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
    return ClinicalCopilotFacade(execute_use_case=ExecuteCopilotRequest(service=service))


class TestClinicalCopilotFacade:
    def test_is_a_clinical_copilot_port(self) -> None:
        assert isinstance(_facade(FakePatientQueryPort()), ClinicalCopilotPort)

    async def test_execute_delegates_to_the_use_case(self) -> None:
        patient_id = uuid4()
        patients = FakePatientQueryPort()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)
        facade = _facade(patients)

        response = await facade.execute(
            AIRequest(request_type="generic", patient_id=patient_id, prompt_version=1)
        )

        assert response.session is not None

    async def test_execute_propagates_errors(self) -> None:
        facade = _facade(FakePatientQueryPort())

        with pytest.raises(PatientNotFoundError):
            await facade.execute(
                AIRequest(request_type="generic", patient_id=uuid4(), prompt_version=1)
            )
