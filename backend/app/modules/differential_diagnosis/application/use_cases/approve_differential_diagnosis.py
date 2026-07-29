"""`ApproveDifferentialDiagnosis` ((Pending|Reviewed) -> Approved) —
allowed from either non-terminal state (`DifferentialDiagnosis
.ensure_editable()`), not only after an explicit `mark_reviewed()` step:
nothing in this task's business rules requires passing through `Reviewed`
first, only that `Approved`/`Rejected` become read-only once reached.
"""

from app.modules.differential_diagnosis.application.dto import (
    ApproveDifferentialDiagnosisInput,
    DifferentialDiagnosisReviewStatusOutput,
)
from app.modules.differential_diagnosis.domain.exceptions import (
    DifferentialDiagnosisNotFoundError,
)
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ApproveDifferentialDiagnosis(
    UseCase[ApproveDifferentialDiagnosisInput, DifferentialDiagnosisReviewStatusOutput]
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
        self, input_dto: ApproveDifferentialDiagnosisInput
    ) -> DifferentialDiagnosisReviewStatusOutput:
        diagnosis = await self._diagnoses.get_by_id(input_dto.differential_diagnosis_id)
        if diagnosis is None:
            raise DifferentialDiagnosisNotFoundError(input_dto.differential_diagnosis_id)

        diagnosis.approve()
        await self._diagnoses.add(diagnosis)
        self._uow.collect_events(diagnosis.pull_events())
        await self._uow.commit()

        return DifferentialDiagnosisReviewStatusOutput(
            differential_diagnosis_id=diagnosis.id,
            clinical_note_id=diagnosis.clinical_note_id,
            review_status=diagnosis.review_status,
        )
