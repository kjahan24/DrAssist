"""`UpdateICD10Coding` — "Approved and Rejected codes become read-only",
enforced solely by `ICD10Coding.ensure_editable()` (this aggregate's own
status self-check, called internally by `update_details()` — raises
`ICD10CodingNotEditableError`). No cross-module port call here — see
`domain/entities.py` for why this module never checks
`ClinicalNoteQueryPort.is_editable`. Only `diagnosis_title`/
`coding_notes` are mutable; `icd10_code`/`coding_source`/
`differential_diagnosis_id` and every identity field are immutable once
set — see `domain/entities.py`.

Does not re-check "duplicate icd10_code" against siblings on update —
that check only applies at creation, the same scope
`app.modules.differential_diagnosis.application.use_cases
.update_differential_diagnosis.UpdateDifferentialDiagnosis` already draws
for its own `diagnosis_name` duplicate check.
"""

from app.modules.icd10_coding.application.dto import (
    UpdateICD10CodingInput,
    UpdateICD10CodingOutput,
)
from app.modules.icd10_coding.domain.exceptions import ICD10CodingNotFoundError
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateICD10Coding(UseCase[UpdateICD10CodingInput, UpdateICD10CodingOutput]):
    def __init__(
        self, *, icd10_coding_repository: ICD10CodingRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._codings = icd10_coding_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateICD10CodingInput) -> UpdateICD10CodingOutput:
        coding = await self._codings.get_by_id(input_dto.icd10_coding_id)
        if coding is None:
            raise ICD10CodingNotFoundError(input_dto.icd10_coding_id)

        coding.update_details(
            diagnosis_title=input_dto.diagnosis_title, coding_notes=input_dto.coding_notes
        )
        await self._codings.add(coding)
        self._uow.collect_events(coding.pull_events())
        await self._uow.commit()

        return UpdateICD10CodingOutput(
            icd10_coding_id=coding.id, clinical_note_id=coding.clinical_note_id
        )
