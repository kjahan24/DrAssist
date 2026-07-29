"""`CreateICD10Coding` — an ICD-10 coding record always references exactly
one existing `ClinicalNote`, and a clinical note may have *many* ICD-10
codes ("One Clinical Note may contain multiple ICD-10 codes") — so, unlike
`CreateSOAPNote`/`CreatePrescription`, this use case performs no "does
this clinical note already have one?" check, the identical shape
`app.modules.differential_diagnosis.application.use_cases
.create_differential_diagnosis.CreateDifferentialDiagnosis` already
establishes for its own one-to-many place under `ClinicalNote`.

Resolves the parent through `ClinicalNoteQueryPort` and derives all four
identity fields — `organization_id`, `patient_id`, `visit_id`,
`doctor_id` — from that single lookup, which is what makes "Patient,
Visit, Doctor, Organization, and Clinical Note must match" true
unconditionally. A missing clinical note raises `ClinicalNoteNotFoundError`
(defined locally — see `domain/exceptions.py` for why).

If `differential_diagnosis_id` is supplied, this use case additionally
resolves it through `DifferentialDiagnosisQueryPort` and checks "both
must belong to the same Clinical Note" — a cross-*module* consistency
check that requires I/O, so it cannot live in the domain layer (see
`domain/entities.py`). A missing differential diagnosis raises
`DifferentialDiagnosisNotFoundError`; a clinical-note mismatch raises
`DifferentialDiagnosisClinicalNoteMismatchError`.

"Duplicate ICD-10 prevention within a Clinical Note" and "Single Primary
ICD-10 validation" are both cross-row checks against sibling codings,
enforced here via repository queries before construction — the identical
"query siblings, then reject" technique
`app.modules.diagnosis.application.use_cases.record_diagnosis
.RecordDiagnosis` already established for `VisitDiagnosis`'s own
sequence/primary uniqueness.

Unlike `CreateSOAPNote`/`CreatePrescription`/`CreateLabOrder` (each of
which also checks `ClinicalNoteQueryPort.is_editable` before creating),
this use case does **not** — this task's business rules never tie
`ICD10Coding` creation (or any of its mutations) to `ClinicalNote`'s own
status; see `domain/entities.py` for the full reasoning.
"""

from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.icd10_coding.application.dto import (
    CreateICD10CodingInput,
    CreateICD10CodingOutput,
)
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DifferentialDiagnosisClinicalNoteMismatchError,
    DifferentialDiagnosisNotFoundError,
    DuplicateICD10CodeError,
    DuplicatePrimaryCodeError,
)
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateICD10Coding(UseCase[CreateICD10CodingInput, CreateICD10CodingOutput]):
    def __init__(
        self,
        *,
        icd10_coding_repository: ICD10CodingRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        differential_diagnosis_query_port: DifferentialDiagnosisQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._codings = icd10_coding_repository
        self._clinical_notes = clinical_note_query_port
        self._differential_diagnoses = differential_diagnosis_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateICD10CodingInput) -> CreateICD10CodingOutput:
        clinical_note_summary = await self._clinical_notes.get_clinical_note_summary(
            input_dto.clinical_note_id
        )
        if clinical_note_summary is None:
            raise ClinicalNoteNotFoundError(input_dto.clinical_note_id)

        if input_dto.differential_diagnosis_id is not None:
            diagnosis_summary = (
                await self._differential_diagnoses.get_differential_diagnosis_summary(
                    input_dto.differential_diagnosis_id
                )
            )
            if diagnosis_summary is None:
                raise DifferentialDiagnosisNotFoundError(input_dto.differential_diagnosis_id)
            if diagnosis_summary.clinical_note_id != input_dto.clinical_note_id:
                raise DifferentialDiagnosisClinicalNoteMismatchError(
                    input_dto.differential_diagnosis_id, input_dto.clinical_note_id
                )

        siblings = await self._codings.list_by_clinical_note(input_dto.clinical_note_id)
        normalized_code = input_dto.icd10_code.strip().upper()
        if any(c.icd10_code == normalized_code for c in siblings):
            raise DuplicateICD10CodeError(input_dto.clinical_note_id, input_dto.icd10_code)

        if input_dto.primary_code:
            existing_primary = await self._codings.get_primary_for_clinical_note(
                input_dto.clinical_note_id
            )
            if existing_primary is not None:
                raise DuplicatePrimaryCodeError(input_dto.clinical_note_id)

        coding = ICD10Coding.create(
            organization_id=clinical_note_summary.organization_id,
            clinical_note_id=input_dto.clinical_note_id,
            patient_id=clinical_note_summary.patient_id,
            visit_id=clinical_note_summary.visit_id,
            doctor_id=clinical_note_summary.doctor_id,
            icd10_code=input_dto.icd10_code,
            diagnosis_title=input_dto.diagnosis_title,
            coding_source=input_dto.coding_source,
            differential_diagnosis_id=input_dto.differential_diagnosis_id,
            primary_code=input_dto.primary_code,
            coding_notes=input_dto.coding_notes,
        )
        await self._codings.add(coding)
        self._uow.collect_events(coding.pull_events())
        await self._uow.commit()

        return CreateICD10CodingOutput(
            icd10_coding_id=coding.id,
            organization_id=coding.organization_id,
            clinical_note_id=coding.clinical_note_id,
            review_status=coding.review_status,
        )
