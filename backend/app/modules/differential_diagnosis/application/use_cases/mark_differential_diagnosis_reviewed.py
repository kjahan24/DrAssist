"""`MarkDifferentialDiagnosisReviewed` (Pending -> Reviewed) — the narrow
transition a doctor takes to acknowledge having looked at an AI/Hybrid-
generated diagnosis before deciding to `approve()`/`reject()` it.
Requires `review_status` to currently be `Pending`
(`DifferentialDiagnosis.mark_reviewed()` raises
`ReviewRequiresPendingStatusError` otherwise) — physician-authored
diagnoses start at `Reviewed` already (see `domain/entities.py`), so this
transition is only ever exercised for AI/Hybrid-generated diagnoses.
"""

from app.modules.differential_diagnosis.application.dto import (
    DifferentialDiagnosisReviewStatusOutput,
    MarkDifferentialDiagnosisReviewedInput,
)
from app.modules.differential_diagnosis.domain.exceptions import (
    DifferentialDiagnosisNotFoundError,
)
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class MarkDifferentialDiagnosisReviewed(
    UseCase[MarkDifferentialDiagnosisReviewedInput, DifferentialDiagnosisReviewStatusOutput]
):
    def __init__(
        self,
        *,
        differential_diagnosis_repository: DifferentialDiagnosisRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._diagnoses = differential_diagnosis_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: MarkDifferentialDiagnosisReviewedInput
    ) -> DifferentialDiagnosisReviewStatusOutput:
        diagnosis = await self._diagnoses.get_by_id(input_dto.differential_diagnosis_id)
        if diagnosis is None:
            raise DifferentialDiagnosisNotFoundError(input_dto.differential_diagnosis_id)

        diagnosis.mark_reviewed()
        await self._diagnoses.add(diagnosis)
        self._uow.collect_events(diagnosis.pull_events())
        await self._uow.commit()

        return DifferentialDiagnosisReviewStatusOutput(
            differential_diagnosis_id=diagnosis.id,
            clinical_note_id=diagnosis.clinical_note_id,
            review_status=diagnosis.review_status,
        )
