"""`CreateDifferentialDiagnosis` — a differential diagnosis always
references exactly one existing `ClinicalNote`, and a clinical note may
have *many* differential diagnoses ("One Clinical Note may have multiple
Differential Diagnoses") — so, unlike `CreateSOAPNote`/
`CreatePrescription`, this use case performs no "does this clinical note
already have one?" check, the identical shape
`app.modules.clinical_reasoning.application.use_cases
.create_clinical_reasoning.CreateClinicalReasoning` already establishes
for its own one-to-many place under `ClinicalNote`.

Resolves the parent through `ClinicalNoteQueryPort` and derives all four
identity fields — `organization_id`, `patient_id`, `visit_id`,
`doctor_id` — from that single lookup, which is what makes "Patient,
Visit, Doctor, and Organization must match the linked Clinical Note" true
unconditionally. A missing clinical note raises `ClinicalNoteNotFoundError`
(defined locally — see `domain/exceptions.py` for why).

If `clinical_reasoning_id` is supplied, this use case additionally
resolves it through `ClinicalReasoningQueryPort` and checks "both records
must belong to the same Clinical Note" — a cross-*module* consistency
check that requires I/O, so it cannot live in the domain layer (see
`domain/entities.py`). A missing reasoning record raises
`ClinicalReasoningNotFoundError`; a clinical-note mismatch raises
`ClinicalReasoningClinicalNoteMismatchError`.

"Ranking must be unique within a Clinical Note" and "Duplicate diagnosis
prevention" (diagnosis_name must be unique, case-insensitively, within a
Clinical Note) are both cross-row checks against sibling diagnoses,
enforced here via repository queries before construction — the identical
"query siblings, then reject" technique
`app.modules.diagnosis.application.use_cases.record_diagnosis
.RecordDiagnosis` already established for `VisitDiagnosis.sequence_number`.

Unlike `CreateSOAPNote`/`CreatePrescription`/`CreateLabOrder` (each of
which also checks `ClinicalNoteQueryPort.is_editable` before creating),
this use case does **not** — this task's business rules never tie
`DifferentialDiagnosis` creation (or any of its mutations) to
`ClinicalNote`'s own status; see `domain/entities.py` for the full
reasoning.
"""

from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.public.interfaces import ClinicalReasoningQueryPort
from app.modules.differential_diagnosis.application.dto import (
    CreateDifferentialDiagnosisInput,
    CreateDifferentialDiagnosisOutput,
)
from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.exceptions import (
    ClinicalNoteNotFoundError,
    ClinicalReasoningClinicalNoteMismatchError,
    ClinicalReasoningNotFoundError,
    DuplicateDiagnosisNameError,
    DuplicateRankingError,
)
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateDifferentialDiagnosis(
    UseCase[CreateDifferentialDiagnosisInput, CreateDifferentialDiagnosisOutput]
):
    def __init__(
        self,
        *,
        differential_diagnosis_repository: DifferentialDiagnosisRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        clinical_reasoning_query_port: ClinicalReasoningQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._diagnoses = differential_diagnosis_repository
        self._clinical_notes = clinical_note_query_port
        self._clinical_reasoning = clinical_reasoning_query_port
        self._uow = unit_of_work

    async def execute(
        self, input_dto: CreateDifferentialDiagnosisInput
    ) -> CreateDifferentialDiagnosisOutput:
        clinical_note_summary = await self._clinical_notes.get_clinical_note_summary(
            input_dto.clinical_note_id
        )
        if clinical_note_summary is None:
            raise ClinicalNoteNotFoundError(input_dto.clinical_note_id)

        if input_dto.clinical_reasoning_id is not None:
            reasoning_summary = await self._clinical_reasoning.get_clinical_reasoning_summary(
                input_dto.clinical_reasoning_id
            )
            if reasoning_summary is None:
                raise ClinicalReasoningNotFoundError(input_dto.clinical_reasoning_id)
            if reasoning_summary.clinical_note_id != input_dto.clinical_note_id:
                raise ClinicalReasoningClinicalNoteMismatchError(
                    input_dto.clinical_reasoning_id, input_dto.clinical_note_id
                )

        existing_ranking = await self._diagnoses.get_by_clinical_note_and_ranking(
            clinical_note_id=input_dto.clinical_note_id, ranking=input_dto.ranking
        )
        if existing_ranking is not None:
            raise DuplicateRankingError(input_dto.clinical_note_id, input_dto.ranking)

        siblings = await self._diagnoses.list_by_clinical_note(input_dto.clinical_note_id)
        normalized_name = input_dto.diagnosis_name.strip().lower()
        if any(s.diagnosis_name.lower() == normalized_name for s in siblings):
            raise DuplicateDiagnosisNameError(input_dto.clinical_note_id, input_dto.diagnosis_name)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=clinical_note_summary.organization_id,
            clinical_note_id=input_dto.clinical_note_id,
            patient_id=clinical_note_summary.patient_id,
            visit_id=clinical_note_summary.visit_id,
            doctor_id=clinical_note_summary.doctor_id,
            diagnosis_name=input_dto.diagnosis_name,
            diagnosis_source=input_dto.diagnosis_source,
            ranking=input_dto.ranking,
            clinical_reasoning_id=input_dto.clinical_reasoning_id,
            likelihood_score=input_dto.likelihood_score,
            supporting_evidence=input_dto.supporting_evidence,
            excluded=input_dto.excluded,
        )
        await self._diagnoses.add(diagnosis)
        self._uow.collect_events(diagnosis.pull_events())
        await self._uow.commit()

        return CreateDifferentialDiagnosisOutput(
            differential_diagnosis_id=diagnosis.id,
            organization_id=diagnosis.organization_id,
            clinical_note_id=diagnosis.clinical_note_id,
            review_status=diagnosis.review_status,
        )
