"""Unit tests for `ClinicalCopilotService` — the 8-stage AI Request
Pipeline (Validation -> Context Assembly -> Prompt Rendering -> Provider
Selection -> LLM Call -> Structured Parsing -> Validation -> Audit
Logging -> Return DTO)."""

from uuid import uuid4

import pytest

from app.modules.ai.public.dto import (
    AIFinishReason,
    AIMessage,
    AIMessageRole,
    AIModel,
    AIProviderType,
    ChatCompletionResponse,
    TokenUsage,
)
from app.modules.ai_copilot.application.services.clinical_copilot_service import (
    ClinicalCopilotService,
)
from app.modules.ai_copilot.application.services.context_builder import ContextBuilder
from app.modules.ai_copilot.application.services.prompt_builder import PromptBuilder
from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.exceptions import (
    AIResponseValidationError,
    PatientNotFoundError,
    StructuredResponseParsingError,
)
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

_DEFAULT_MODEL = AIModel(provider=AIProviderType.MOCK, name="mock-model")


def _build_service(
    *,
    patients: FakePatientQueryPort | None = None,
    ai_gateway: FakeAIGateway | None = None,
    output_parser: FakeCopilotOutputParser | None = None,
    response_validator: FakeAIResponseValidator | None = None,
    audit_logger: FakeCopilotAuditLogger | None = None,
    cost_estimator: FakeCostEstimator | None = None,
) -> tuple[ClinicalCopilotService, FakePatientQueryPort, FakeAIGateway, FakeCopilotAuditLogger]:
    patients = patients or FakePatientQueryPort()
    gateway = ai_gateway or FakeAIGateway()
    audit = audit_logger or FakeCopilotAuditLogger()
    context_builder = ContextBuilder(
        patient_query_port=patients,
        prescription_query_port=FakePrescriptionQueryPort(),
        visit_query_port=FakeVisitQueryPort(),
        clinical_note_query_port=FakeClinicalNoteQueryPort(),
        soap_note_query_port=FakeSOAPNoteQueryPort(),
        lab_result_query_port=FakeLabResultQueryPort(),
        timeline_query_port=FakeTimelineQueryPort(),
    )
    service = ClinicalCopilotService(
        context_builder=context_builder,
        prompt_builder=PromptBuilder(ai_gateway=gateway),
        ai_gateway=gateway,
        output_parser=output_parser or FakeCopilotOutputParser(),
        response_validator=response_validator or FakeAIResponseValidator(),
        audit_logger=audit,
        cost_estimator=cost_estimator or FakeCostEstimator(),
        default_model=_DEFAULT_MODEL,
    )
    return service, patients, gateway, audit


def _request(patient_id: object, **overrides: object) -> AIRequest:
    defaults: dict[str, object] = {
        "request_type": "generic",
        "patient_id": patient_id,
        "prompt_version": 1,
    }
    defaults.update(overrides)
    return AIRequest(**defaults)  # type: ignore[arg-type]


class TestClinicalCopilotServiceHappyPath:
    async def test_returns_an_ai_response_with_parsed_content_and_session(self) -> None:
        patient_id = uuid4()
        service, patients, _gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        response = await service.execute(_request(patient_id))

        assert response.parsed_content == {"parsed": '{"result": "ok"}'}
        assert response.session.request_id is not None
        assert response.session.provider == "mock"

    async def test_two_executions_produce_different_request_ids(self) -> None:
        patient_id = uuid4()
        service, patients, _gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        first = await service.execute(_request(patient_id))
        second = await service.execute(_request(patient_id))

        assert first.session.request_id != second.session.request_id

    async def test_latency_is_recorded_as_non_negative(self) -> None:
        patient_id = uuid4()
        service, patients, _gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        response = await service.execute(_request(patient_id))

        assert response.session.latency_ms >= 0

    async def test_records_prompt_name_and_version_on_the_session(self) -> None:
        patient_id = uuid4()
        service, patients, _gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        response = await service.execute(
            _request(patient_id, request_type="soap_note", prompt_version=4)
        )

        assert response.session.prompt_name == "soap_note"
        assert response.session.prompt_version == 4

    async def test_records_token_usage_on_the_session(self) -> None:
        patient_id = uuid4()
        service, patients, _gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        response = await service.execute(_request(patient_id))

        assert response.session.prompt_tokens == 10
        assert response.session.completion_tokens == 5
        assert response.session.total_tokens == 15

    async def test_records_estimated_cost_from_the_injected_cost_estimator(self) -> None:
        patient_id = uuid4()
        cost_estimator = FakeCostEstimator(fixed_cost=0.0099)
        service, patients, _gateway, _audit = _build_service(cost_estimator=cost_estimator)
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        response = await service.execute(_request(patient_id))

        assert response.session.estimated_cost_usd == 0.0099
        assert len(cost_estimator.calls) == 1

    async def test_logs_a_session_on_success(self) -> None:
        patient_id = uuid4()
        service, patients, _gateway, audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await service.execute(_request(patient_id))

        assert len(audit.sessions) == 1
        assert audit.failures == []

    async def test_uses_model_override_when_given(self) -> None:
        patient_id = uuid4()
        service, patients, gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await service.execute(_request(patient_id, model_override="mock-large"))

        assert gateway.received_chat_requests[-1].model.name == "mock-large"
        assert gateway.received_chat_requests[-1].model.provider == _DEFAULT_MODEL.provider

    async def test_uses_default_model_when_no_override_given(self) -> None:
        patient_id = uuid4()
        service, patients, gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await service.execute(_request(patient_id))

        assert gateway.received_chat_requests[-1].model == _DEFAULT_MODEL

    async def test_extra_variables_reach_the_rendered_prompt_call(self) -> None:
        patient_id = uuid4()
        service, patients, gateway, _audit = _build_service()
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await service.execute(_request(patient_id, variables={"tone": "concise"}))

        # No direct assertion on PromptVariables content here (opaque to
        # the fake) — this asserts the pipeline did not error out while
        # threading extra variables through context -> prompt building.
        assert len(gateway.rendered_calls) == 3


class TestClinicalCopilotServiceFailureModes:
    async def test_unknown_patient_raises_and_logs_a_failure(self) -> None:
        service, _patients, _gateway, audit = _build_service()

        with pytest.raises(PatientNotFoundError):
            await service.execute(_request(uuid4()))

        assert len(audit.failures) == 1
        assert audit.failures[0]["stage"] == "context_assembly"
        assert audit.failures[0]["error_code"] == "PatientNotFoundError"
        assert audit.sessions == []

    async def test_parsing_failure_raises_and_logs_a_failure(self) -> None:
        patient_id = uuid4()
        parser = FakeCopilotOutputParser(error=StructuredResponseParsingError("json", "bad token"))
        service, patients, _gateway, audit = _build_service(output_parser=parser)
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        with pytest.raises(StructuredResponseParsingError):
            await service.execute(_request(patient_id))

        assert audit.failures[0]["stage"] == "parsing"
        assert audit.sessions == []

    async def test_response_validation_failure_raises_and_logs_a_failure(self) -> None:
        patient_id = uuid4()
        validator = FakeAIResponseValidator(error=AIResponseValidationError("empty response"))
        service, patients, _gateway, audit = _build_service(response_validator=validator)
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        with pytest.raises(AIResponseValidationError):
            await service.execute(_request(patient_id))

        assert audit.failures[0]["stage"] == "validation"
        assert audit.sessions == []

    async def test_ai_foundation_errors_propagate_unwrapped(self) -> None:
        patient_id = uuid4()

        class _FakeFoundationError(Exception):
            pass

        gateway = FakeAIGateway(chat_error=_FakeFoundationError("provider unavailable"))
        service, patients, _gateway, audit = _build_service(ai_gateway=gateway)
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        with pytest.raises(_FakeFoundationError):
            await service.execute(_request(patient_id))

        # This module does not catch/log AI-Foundation-originated errors
        # (see domain/exceptions.py's module docstring) — no failure
        # record is expected here.
        assert audit.failures == []


class TestClinicalCopilotServicePipelineOrdering:
    async def test_output_parser_receives_the_llm_reply_content(self) -> None:
        patient_id = uuid4()
        gateway = FakeAIGateway(
            chat_response=ChatCompletionResponse(
                message=AIMessage(role=AIMessageRole.ASSISTANT, content="raw llm text"),
                model=_DEFAULT_MODEL,
                provider=AIProviderType.MOCK,
                usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
                finish_reason=AIFinishReason.STOP,
                latency_ms=1.0,
            )
        )
        parser = FakeCopilotOutputParser()
        service, patients, _gateway, _audit = _build_service(
            ai_gateway=gateway, output_parser=parser
        )
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await service.execute(_request(patient_id))

        assert parser.received[0][0] == "raw llm text"
        assert parser.received[0][1] is CopilotOutputFormat.JSON

    async def test_response_validator_receives_the_parsed_content(self) -> None:
        patient_id = uuid4()
        parser = FakeCopilotOutputParser(result={"key": "value"})
        validator = FakeAIResponseValidator()
        service, patients, _gateway, _audit = _build_service(
            output_parser=parser, response_validator=validator
        )
        patients.patients[patient_id] = make_patient_summary(patient_id=patient_id)

        await service.execute(_request(patient_id))

        assert validator.received == [{"key": "value"}]
