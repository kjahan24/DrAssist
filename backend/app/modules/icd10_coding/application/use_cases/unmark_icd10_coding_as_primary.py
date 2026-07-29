"""`UnmarkICD10CodingAsPrimary` — the mirror of `MarkICD10CodingAsPrimary`.
Demoting a code from Primary can never violate "only one Primary per
Clinical Note", so — unlike promoting — this use case needs no sibling
query before calling `ICD10Coding.unmark_as_primary()`.
"""

from app.modules.icd10_coding.application.dto import (
    ICD10CodingPrimaryOutput,
    UnmarkICD10CodingAsPrimaryInput,
)
from app.modules.icd10_coding.domain.exceptions import ICD10CodingNotFoundError
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UnmarkICD10CodingAsPrimary(
    UseCase[UnmarkICD10CodingAsPrimaryInput, ICD10CodingPrimaryOutput]
):
    def __init__(
        self, *, icd10_coding_repository: ICD10CodingRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._codings = icd10_coding_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UnmarkICD10CodingAsPrimaryInput) -> ICD10CodingPrimaryOutput:
        coding = await self._codings.get_by_id(input_dto.icd10_coding_id)
        if coding is None:
            raise ICD10CodingNotFoundError(input_dto.icd10_coding_id)

        coding.unmark_as_primary()
        await self._codings.add(coding)
        self._uow.collect_events(coding.pull_events())
        await self._uow.commit()

        return ICD10CodingPrimaryOutput(
            icd10_coding_id=coding.id,
            clinical_note_id=coding.clinical_note_id,
            primary_code=coding.primary_code,
        )
