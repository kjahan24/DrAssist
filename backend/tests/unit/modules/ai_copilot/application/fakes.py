"""In-memory test doubles for the seven peer modules'
public query ports `ContextBuilder` depends on, plus AI Foundation's own
`AIGatewayPort` and this module's own application-layer ports — per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"), each implements the exact same interface its real
counterpart does.

Factory functions (`make_*_summary`) build minimally-valid DTO instances
with sensible defaults, overridable via keyword arguments, so individual
tests only need to specify the fields they actually care about.
"""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.ai.public.dto import (
    AIFinishReason,
    AIMessage,
    AIMessageRole,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    PromptVariables,
    TokenUsage,
)
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.ai_copilot.application.ports import (
    AIResponseValidatorPort,
    CopilotAuditLoggerPort,
    CopilotOutputParserPort,
)
from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.value_objects import AISession
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_results.domain.enums import AbnormalFlag, LabResultStatus
from app.modules.lab_results.public.dto import LabResultItemSummaryDTO, LabResultSummaryDTO
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient.domain.enums import (
    AllergySeverity,
    AllergyStatus,
    AllergyType,
    ConditionSeverity,
    ConditionStatus,
    Gender,
    PatientStatus,
)
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.prescriptions.domain.enums import AdministrationRoute, PrescriptionStatus
from app.modules.prescriptions.public.dto import (
    PrescriptionItemSummaryDTO,
    PrescriptionSummaryDTO,
)
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.modules.timeline.domain.enums import (
    TimelineEventCategory,
    TimelineEventType,
    TimelineSourceModule,
)
from app.modules.timeline.public.dto import TimelineEventDTO, TimelineFilterInput, TimelinePageDTO
from app.modules.timeline.public.interfaces import TimelineQueryPort
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort

# --- DTO factories ---------------------------------------------------


def make_patient_summary(**overrides: object) -> PatientSummaryDTO:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "organization_id": uuid4(),
        "patient_number": "PAT-0001",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1990, 1, 1),
        "status": PatientStatus.ACTIVE,
    }
    defaults.update(overrides)
    return PatientSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_allergy_summary(*, patient_id: UUID, **overrides: object) -> PatientAllergySummaryDTO:
    defaults: dict[str, object] = {
        "allergy_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": patient_id,
        "allergy_type": AllergyType.DRUG,
        "allergen_name": "Penicillin",
        "severity": AllergySeverity.SEVERE,
        "reaction": "hives",
        "onset_date": None,
        "status": AllergyStatus.ACTIVE,
        "notes": None,
        "verified_by": None,
        "verified_date": None,
    }
    defaults.update(overrides)
    return PatientAllergySummaryDTO(**defaults)  # type: ignore[arg-type]


def make_condition_summary(
    *, patient_id: UUID, **overrides: object
) -> PatientMedicalConditionSummaryDTO:
    defaults: dict[str, object] = {
        "condition_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": patient_id,
        "diagnosed_by": None,
        "condition_name": "Hypertension",
        "icd10_code": "I10",
        "category": "cardiovascular",
        "severity": ConditionSeverity.MODERATE,
        "diagnosis_date": date(2020, 1, 1),
        "onset_date": None,
        "status": ConditionStatus.CHRONIC,
        "is_chronic": True,
        "is_infectious": False,
        "notes": None,
        "resolved_date": None,
    }
    defaults.update(overrides)
    return PatientMedicalConditionSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_prescription_item(**overrides: object) -> PrescriptionItemSummaryDTO:
    defaults: dict[str, object] = {
        "prescription_item_id": uuid4(),
        "prescription_id": uuid4(),
        "medication_name": "Lisinopril",
        "strength": "10mg",
        "dosage": "1 tablet",
        "dosage_unit": "tablet",
        "frequency": "once daily",
        "route": AdministrationRoute.ORAL,
        "duration": "30",
        "duration_unit": "days",
        "quantity": "30",
        "generic_name": None,
        "instructions": None,
    }
    defaults.update(overrides)
    return PrescriptionItemSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_prescription_summary(*, patient_id: UUID, **overrides: object) -> PrescriptionSummaryDTO:
    defaults: dict[str, object] = {
        "prescription_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": patient_id,
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "prescription_number": "RX-0001",
        "prescription_date": date(2024, 1, 1),
        "status": PrescriptionStatus.FINAL,
        "notes": None,
        "items": [make_prescription_item()],
    }
    defaults.update(overrides)
    return PrescriptionSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_visit_summary(*, patient_id: UUID, **overrides: object) -> VisitSummaryDTO:
    defaults: dict[str, object] = {
        "visit_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": patient_id,
        "doctor_id": uuid4(),
        "visit_number": "V-0001",
        "visit_status": VisitStatus.SCHEDULED,
        "visit_date": date(2024, 1, 1),
        "reason_for_visit": "Annual checkup",
    }
    defaults.update(overrides)
    return VisitSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_clinical_note_summary(*, patient_id: UUID, **overrides: object) -> ClinicalNoteSummaryDTO:
    defaults: dict[str, object] = {
        "clinical_note_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": patient_id,
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "note_number": "CN-0001",
        "note_type": ClinicalNoteType.INITIAL,
        "status": ClinicalNoteStatus.SIGNED,
        "encounter_datetime": datetime(2024, 1, 1, tzinfo=UTC),
        "ai_generated": False,
        "assessment_summary": "Stable, no acute findings.",
    }
    defaults.update(overrides)
    return ClinicalNoteSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_soap_note_summary(*, clinical_note_id: UUID, **overrides: object) -> SOAPNoteSummaryDTO:
    defaults: dict[str, object] = {
        "soap_note_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": clinical_note_id,
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "chief_complaint": "Headache",
        "history_of_present_illness": None,
        "review_of_systems": None,
        "physical_examination": None,
        "vital_sign_summary": None,
        "assessment": "Tension headache",
        "plan": "OTC analgesics",
    }
    defaults.update(overrides)
    return SOAPNoteSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_lab_result_item(**overrides: object) -> LabResultItemSummaryDTO:
    defaults: dict[str, object] = {
        "lab_result_item_id": uuid4(),
        "lab_result_id": uuid4(),
        "lab_order_item_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "result_value": "normal",
        "abnormal_flag": AbnormalFlag.NORMAL,
        "result_unit": None,
        "reference_range": None,
        "interpretation": None,
    }
    defaults.update(overrides)
    return LabResultItemSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_lab_result_summary(*, patient_id: UUID, **overrides: object) -> LabResultSummaryDTO:
    defaults: dict[str, object] = {
        "lab_result_id": uuid4(),
        "organization_id": uuid4(),
        "lab_order_id": uuid4(),
        "patient_id": patient_id,
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "result_number": "LR-0001",
        "reported_at": datetime(2024, 1, 1, tzinfo=UTC),
        "status": LabResultStatus.FINAL,
        "laboratory_name": "Central Lab",
        "comments": None,
        "items": [make_lab_result_item()],
    }
    defaults.update(overrides)
    return LabResultSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_timeline_event(*, patient_id: UUID, **overrides: object) -> TimelineEventDTO:
    defaults: dict[str, object] = {
        "event_id": uuid4(),
        "event_type": TimelineEventType.VISIT,
        "event_category": TimelineEventCategory.SCHEDULING,
        "patient_id": patient_id,
        "organization_id": uuid4(),
        "reference_id": uuid4(),
        "title": "Visit completed",
        "summary": None,
        "event_datetime": datetime(2024, 1, 1, tzinfo=UTC),
        "source_module": TimelineSourceModule.VISIT,
        "icon_key": "calendar",
        "color_key": "blue",
    }
    defaults.update(overrides)
    return TimelineEventDTO(**defaults)  # type: ignore[arg-type]


# --- Fake query ports --------------------------------------------------


class FakePatientQueryPort(PatientQueryPort):
    def __init__(self) -> None:
        self.patients: dict[UUID, PatientSummaryDTO] = {}
        self.allergies: dict[UUID, list[PatientAllergySummaryDTO]] = {}
        self.conditions: dict[UUID, list[PatientMedicalConditionSummaryDTO]] = {}

    async def patient_exists(self, patient_id: UUID) -> bool:
        return patient_id in self.patients

    async def is_active(self, patient_id: UUID) -> bool:
        return patient_id in self.patients

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        return self.patients.get(patient_id)

    async def list_allergies_for_patient(self, patient_id: UUID) -> list[PatientAllergySummaryDTO]:
        return self.allergies.get(patient_id, [])

    async def list_medical_conditions_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicalConditionSummaryDTO]:
        return self.conditions.get(patient_id, [])


class FakePrescriptionQueryPort(PrescriptionQueryPort):
    def __init__(self) -> None:
        self.prescriptions_by_patient: dict[UUID, list[PrescriptionSummaryDTO]] = {}

    async def prescription_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return False

    async def get_prescription_summary(
        self, clinical_note_id: UUID
    ) -> PrescriptionSummaryDTO | None:
        return None

    async def list_prescriptions_for_patient(
        self, patient_id: UUID
    ) -> list[PrescriptionSummaryDTO]:
        return self.prescriptions_by_patient.get(patient_id, [])


class FakeVisitQueryPort(VisitQueryPort):
    def __init__(self) -> None:
        self.visits_by_patient: dict[UUID, list[VisitSummaryDTO]] = {}

    async def visit_exists(self, visit_id: UUID) -> bool:
        return False

    async def is_active(self, visit_id: UUID) -> bool:
        return False

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        return None

    async def list_visits_for_patient(self, patient_id: UUID) -> list[VisitSummaryDTO]:
        return self.visits_by_patient.get(patient_id, [])


class FakeClinicalNoteQueryPort(ClinicalNoteQueryPort):
    def __init__(self) -> None:
        self.notes_by_patient: dict[UUID, list[ClinicalNoteSummaryDTO]] = {}

    async def clinical_note_exists(self, clinical_note_id: UUID) -> bool:
        return False

    async def is_editable(self, clinical_note_id: UUID) -> bool:
        return False

    async def get_clinical_note_summary(
        self, clinical_note_id: UUID
    ) -> ClinicalNoteSummaryDTO | None:
        return None

    async def list_clinical_notes_for_visit(self, visit_id: UUID) -> list[ClinicalNoteSummaryDTO]:
        return []

    async def list_clinical_notes_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalNoteSummaryDTO]:
        return self.notes_by_patient.get(patient_id, [])


class FakeSOAPNoteQueryPort(SOAPNoteQueryPort):
    def __init__(self) -> None:
        self.soap_notes_by_clinical_note: dict[UUID, SOAPNoteSummaryDTO] = {}

    async def soap_note_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.soap_notes_by_clinical_note

    async def get_soap_note_summary(self, clinical_note_id: UUID) -> SOAPNoteSummaryDTO | None:
        return self.soap_notes_by_clinical_note.get(clinical_note_id)


class FakeLabResultQueryPort(LabResultQueryPort):
    def __init__(self) -> None:
        self.results_by_patient: dict[UUID, list[LabResultSummaryDTO]] = {}

    async def lab_result_exists_for_lab_order(self, lab_order_id: UUID) -> bool:
        return False

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return False

    async def get_lab_result_summary(self, lab_order_id: UUID) -> LabResultSummaryDTO | None:
        return None

    async def list_lab_results_for_patient(self, patient_id: UUID) -> list[LabResultSummaryDTO]:
        return self.results_by_patient.get(patient_id, [])


class FakeTimelineQueryPort(TimelineQueryPort):
    def __init__(self) -> None:
        self.events_by_patient: dict[UUID, list[TimelineEventDTO]] = {}
        self.received_filters: list[TimelineFilterInput] = []

    async def get_patient_timeline(
        self,
        patient_id: UUID,
        *,
        filters: TimelineFilterInput,
        offset: int = 0,
        limit: int = 20,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> TimelinePageDTO:
        self.received_filters.append(filters)
        events = self.events_by_patient.get(patient_id, [])
        page = events[offset : offset + limit]
        return TimelinePageDTO(items=page, total=len(events), offset=offset, limit=limit)


# --- Fake AI Foundation gateway -----------------------------------------


class FakeAIGateway(AIGatewayPort):
    def __init__(
        self,
        *,
        chat_response: ChatCompletionResponse | None = None,
        rendered_prompts: dict[str, str] | None = None,
        chat_error: Exception | None = None,
    ) -> None:
        self._chat_response = chat_response
        self._rendered_prompts = rendered_prompts or {}
        self._chat_error = chat_error
        self.received_chat_requests: list[ChatCompletionRequest] = []
        self.rendered_calls: list[tuple[str, int | None]] = []

    async def generate_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        self.received_chat_requests.append(request)
        if self._chat_error is not None:
            raise self._chat_error
        if self._chat_response is not None:
            return self._chat_response
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content='{"result": "ok"}'),
            model=request.model,
            provider=request.model.provider,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason=AIFinishReason.STOP,
            latency_ms=1.0,
        )

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            embeddings=tuple((0.0,) for _ in request.input_texts),
            model=request.model,
            provider=request.model.provider,
        )

    async def render_prompt(
        self, name: str, variables: PromptVariables, *, version: int | None = None
    ) -> str:
        self.rendered_calls.append((name, version))
        if name in self._rendered_prompts:
            return self._rendered_prompts[name]
        return f"rendered:{name}:v{version}"


# --- Fake copilot-owned ports --------------------------------------------


class FakeCopilotOutputParser(CopilotOutputParserPort):
    def __init__(self, *, result: object = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.received: list[tuple[str, CopilotOutputFormat]] = []

    def parse(self, raw_text: str, output_format: CopilotOutputFormat) -> object:
        self.received.append((raw_text, output_format))
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        return {"parsed": raw_text}


class FakeAIResponseValidator(AIResponseValidatorPort):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.received: list[object] = []

    def validate(
        self, parsed_content: object, *, output_format: CopilotOutputFormat, raw_text: str
    ) -> None:
        self.received.append(parsed_content)
        if self._error is not None:
            raise self._error


class FakeCopilotAuditLogger(CopilotAuditLoggerPort):
    def __init__(self) -> None:
        self.sessions: list[AISession] = []
        self.failures: list[dict[str, object]] = []

    async def log_session(self, session: AISession, *, request_type: str, patient_id: UUID) -> None:
        self.sessions.append(session)

    async def log_failure(
        self,
        *,
        request_id: UUID,
        request_type: str,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None:
        self.failures.append(
            {
                "request_id": request_id,
                "request_type": request_type,
                "patient_id": patient_id,
                "stage": stage,
                "error_code": error_code,
                "message": message,
            }
        )


class FakeCostEstimator:
    def __init__(self, *, fixed_cost: float = 0.0042) -> None:
        self._fixed_cost = fixed_cost
        self.calls: list[dict[str, object]] = []

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        self.calls.append(
            {
                "provider": provider,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        )
        return self._fixed_cost
