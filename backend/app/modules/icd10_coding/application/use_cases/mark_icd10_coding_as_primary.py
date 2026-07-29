"""`MarkICD10CodingAsPrimary` — "Only one ICD-10 code can be marked as
Primary" (this task's own Business Rules, the identical shape
`app.modules.diagnosis.application.use_cases.record_diagnosis
.RecordDiagnosis` already establishes for `VisitDiagnosis`'s own primary-
per-visit uniqueness). Because sibling rows are a different aggregate
instance from the one being promoted, this cross-row check cannot live
in `ICD10Coding.mark_as_primary()` itself (see `domain/entities.py`) — it
is enforced here, by querying `ICD10CodingRepository
.get_primary_for_clinical_note` before calling `mark_as_primary()`, and
raising `DuplicatePrimaryCodeError` if a sibling code is already primary.
"""

from app.modules.icd10_coding.application.dto import (
    ICD10CodingPrimaryOutput,
    MarkICD10CodingAsPrimaryInput,
)
from app.modules.icd10_coding.domain.exceptions import (
    DuplicatePrimaryCodeError,
    ICD10CodingNotFoundError,
)
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class MarkICD10CodingAsPrimary(UseCase[MarkICD10CodingAsPrimaryInput, ICD10CodingPrimaryOutput]):
    def __init__(
        self, *, icd10_coding_repository: ICD10CodingRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._codings = icd10_coding_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: MarkICD10CodingAsPrimaryInput) -> ICD10CodingPrimaryOutput:
        coding = await self._codings.get_by_id(input_dto.icd10_coding_id)
        if coding is None:
            raise ICD10CodingNotFoundError(input_dto.icd10_coding_id)

        if not coding.primary_code:
            existing_primary = await self._codings.get_primary_for_clinical_note(
                coding.clinical_note_id
            )
            if existing_primary is not None and existing_primary.id != coding.id:
                raise DuplicatePrimaryCodeError(coding.clinical_note_id)

        coding.mark_as_primary()
        await self._codings.add(coding)
        self._uow.collect_events(coding.pull_events())
        await self._uow.commit()

        return ICD10CodingPrimaryOutput(
            icd10_coding_id=coding.id,
            clinical_note_id=coding.clinical_note_id,
            primary_code=coding.primary_code,
        )
