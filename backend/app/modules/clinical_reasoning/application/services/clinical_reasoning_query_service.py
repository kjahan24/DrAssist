"""Read-only queries against `ClinicalReasoning`.

Backs the module's public `ClinicalReasoningQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

Shaped like `app.modules.lab_orders.application.services
.lab_order_query_service.LabOrderQueryService`, not
`app.modules.prescriptions.application.services
.prescription_query_service.PrescriptionQueryService`:
`ClinicalReasoning` is one-to-*many* with `ClinicalNote` ("One Clinical
Note may contain multiple Clinical Reasoning records"), so
`list_clinical_reasoning_for_clinical_note` — not a single
`get_..._summary(clinical_note_id)` — is the query keyed by the parent;
`get_clinical_reasoning_summary` is instead keyed by this aggregate's own
id. `is_editable` mirrors `LabOrderQueryService.is_editable`'s own
boolean-not-enum shape, for the identical reason: a future module (AI
Copilot/Human Review Workflow, in particular) needs to ask "can this
reasoning record still be modified?" without importing `ReviewStatus`
across the module boundary. `list_clinical_reasoning_for_patient` exists
for the same reason
`app.modules.clinical_notes.application.services.clinical_note_query_service
.ClinicalNoteQueryService.list_clinical_notes_for_patient` does: so a
future Clinical Timeline module can assemble a patient's full reasoning
history across clinical notes without this module needing to change.

Depends on a single repository (unlike `PrescriptionQueryService`/
`LabOrderQueryService`/`LabResultQueryService`) — this task's own field
list gives `ClinicalReasoning` no child "item" entity, so there is no
second repository to embed.
"""

from uuid import UUID

from app.modules.clinical_reasoning.application.dto import ClinicalReasoningSummaryDTO
from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.enums import ReviewStatus
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository

_NOT_EDITABLE_STATUSES = frozenset({ReviewStatus.APPROVED, ReviewStatus.REJECTED})


class ClinicalReasoningQueryService:
    def __init__(self, *, clinical_reasoning_repository: ClinicalReasoningRepository) -> None:
        self._reasoning_records = clinical_reasoning_repository

    async def clinical_reasoning_exists(self, clinical_reasoning_id: UUID) -> bool:
        return await self._reasoning_records.get_by_id(clinical_reasoning_id) is not None

    async def is_editable(self, clinical_reasoning_id: UUID) -> bool:
        reasoning = await self._reasoning_records.get_by_id(clinical_reasoning_id)
        return reasoning is not None and reasoning.review_status not in _NOT_EDITABLE_STATUSES

    async def get_clinical_reasoning_summary(
        self, clinical_reasoning_id: UUID
    ) -> ClinicalReasoningSummaryDTO | None:
        reasoning = await self._reasoning_records.get_by_id(clinical_reasoning_id)
        return _to_summary(reasoning) if reasoning is not None else None

    async def list_clinical_reasoning_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
        records = await self._reasoning_records.list_by_clinical_note(clinical_note_id)
        return [_to_summary(record) for record in records]

    async def list_clinical_reasoning_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
        records = await self._reasoning_records.list_by_patient(patient_id)
        return [_to_summary(record) for record in records]


def _to_summary(reasoning: ClinicalReasoning) -> ClinicalReasoningSummaryDTO:
    return ClinicalReasoningSummaryDTO(
        clinical_reasoning_id=reasoning.id,
        organization_id=reasoning.organization_id,
        clinical_note_id=reasoning.clinical_note_id,
        patient_id=reasoning.patient_id,
        visit_id=reasoning.visit_id,
        doctor_id=reasoning.doctor_id,
        reasoning_source=reasoning.reasoning_source,
        reasoning_text=reasoning.reasoning_text,
        ai_generated=reasoning.ai_generated,
        review_status=reasoning.review_status,
        reviewed_by_doctor=reasoning.reviewed_by_doctor,
        confidence_score=reasoning.confidence_score,
    )
