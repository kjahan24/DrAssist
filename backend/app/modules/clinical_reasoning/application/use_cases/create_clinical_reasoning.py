"""`CreateClinicalReasoning` — a clinical reasoning record always
references exactly one existing `ClinicalNote`, and a clinical note may
have *many* reasoning records ("One Clinical Note may contain multiple
Clinical Reasoning records") — so, unlike `CreateSOAPNote`/
`CreatePrescription`, this use case performs no "does this clinical note
already have one?" check, the identical shape
`app.modules.lab_orders.application.use_cases.create_lab_order
.CreateLabOrder` already establishes for its own one-to-many place under
`ClinicalNote`.

Resolves the parent through `ClinicalNoteQueryPort` and derives all four
identity fields — `organization_id`, `patient_id`, `visit_id`,
`doctor_id` — from that single lookup, which is what makes "Patient,
Visit, Doctor, and Organization must match the linked Clinical Note" true
unconditionally. A missing clinical note raises `ClinicalNoteNotFoundError`
(defined locally — see `domain/exceptions.py` for why).

Unlike `CreateSOAPNote`/`CreatePrescription`/`CreateLabOrder` (each of
which also checks `ClinicalNoteQueryPort.is_editable` before creating),
this use case does **not** — this task's business rules never tie
`ClinicalReasoning` creation (or any of its mutations) to `ClinicalNote`'s
own status; see `domain/entities.py` for the full reasoning.
"""

from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.application.dto import (
    CreateClinicalReasoningInput,
    CreateClinicalReasoningOutput,
)
from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.exceptions import ClinicalNoteNotFoundError
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateClinicalReasoning(UseCase[CreateClinicalReasoningInput, CreateClinicalReasoningOutput]):
    def __init__(
        self,
        *,
        clinical_reasoning_repository: ClinicalReasoningRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reasoning_records = clinical_reasoning_repository
        self._clinical_notes = clinical_note_query_port
        self._uow = unit_of_work

    async def execute(
        self, input_dto: CreateClinicalReasoningInput
    ) -> CreateClinicalReasoningOutput:
        clinical_note_summary = await self._clinical_notes.get_clinical_note_summary(
            input_dto.clinical_note_id
        )
        if clinical_note_summary is None:
            raise ClinicalNoteNotFoundError(input_dto.clinical_note_id)

        reasoning = ClinicalReasoning.create(
            organization_id=clinical_note_summary.organization_id,
            clinical_note_id=input_dto.clinical_note_id,
            patient_id=clinical_note_summary.patient_id,
            visit_id=clinical_note_summary.visit_id,
            doctor_id=clinical_note_summary.doctor_id,
            reasoning_source=input_dto.reasoning_source,
            reasoning_text=input_dto.reasoning_text,
            ai_generated=input_dto.ai_generated,
            confidence_score=input_dto.confidence_score,
        )
        await self._reasoning_records.add(reasoning)
        self._uow.collect_events(reasoning.pull_events())
        await self._uow.commit()

        return CreateClinicalReasoningOutput(
            clinical_reasoning_id=reasoning.id,
            organization_id=reasoning.organization_id,
            clinical_note_id=reasoning.clinical_note_id,
            review_status=reasoning.review_status,
        )
