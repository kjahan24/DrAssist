"""`RejectDifferentialDiagnosis` ((Pending|Reviewed) -> Rejected) — the
mirror of `ApproveDifferentialDiagnosis`; see that use case's own
docstring for why it is allowed from either non-terminal state.
"""

from app.modules.differential_diagnosis.application.dto import (
    DifferentialDiagnosisReviewStatusOutput,
    RejectDifferentialDiagnosisInput,
)
from app.modules.differential_diagnosis.domain.exceptions import (
    DifferentialDiagnosisNotFoundError,
)
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RejectDifferentialDiagnosis(
    UseCase[RejectDifferentialDiagnosisInput, DifferentialDiagnosisReviewStatusOutput]
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
        self, input_dto: RejectDifferentialDiagnosisInput
    ) -> DifferentialDiagnosisReviewStatusOutput:
        diagnosis = await self._diagnoses.get_by_id(input_dto.differential_diagnosis_id)
        if diagnosis is None:
            raise DifferentialDiagnosisNotFoundError(input_dto.differential_diagnosis_id)

        diagnosis.reject()
        await self._diagnoses.add(diagnosis)
        self._uow.collect_events(diagnosis.pull_events())
        await self._uow.commit()

        return DifferentialDiagnosisReviewStatusOutput(
            differential_diagnosis_id=diagnosis.id,
            clinical_note_id=diagnosis.clinical_note_id,
            review_status=diagnosis.review_status,
        )
