"""`UpdateDifferentialDiagnosis` — "Approved and Rejected diagnoses become
read-only", enforced solely by `DifferentialDiagnosis.ensure_editable()`
(this aggregate's own status self-check, called internally by
`update_details()` — raises `DifferentialDiagnosisNotEditableError`). No
cross-module port call here — see `domain/entities.py` for why this
module never checks `ClinicalNoteQueryPort.is_editable`. Only
`diagnosis_name`/`likelihood_score`/`supporting_evidence`/`excluded` are
mutable; `ranking`/`diagnosis_source`/`clinical_reasoning_id` and every
identity field are immutable once set — see `domain/entities.py`.

Does not re-check "duplicate diagnosis_name" against siblings on update —
that check only applies at creation, the same scope
`app.modules.diagnosis.domain.entities.VisitDiagnosis.update_details`
already draws by never re-validating `sequence_number` uniqueness either.
"""

from app.modules.differential_diagnosis.application.dto import (
    UpdateDifferentialDiagnosisInput,
    UpdateDifferentialDiagnosisOutput,
)
from app.modules.differential_diagnosis.domain.exceptions import (
    DifferentialDiagnosisNotFoundError,
)
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateDifferentialDiagnosis(
    UseCase[UpdateDifferentialDiagnosisInput, UpdateDifferentialDiagnosisOutput]
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
        self, input_dto: UpdateDifferentialDiagnosisInput
    ) -> UpdateDifferentialDiagnosisOutput:
        diagnosis = await self._diagnoses.get_by_id(input_dto.differential_diagnosis_id)
        if diagnosis is None:
            raise DifferentialDiagnosisNotFoundError(input_dto.differential_diagnosis_id)

        diagnosis.update_details(
            diagnosis_name=input_dto.diagnosis_name,
            likelihood_score=input_dto.likelihood_score,
            supporting_evidence=input_dto.supporting_evidence,
            excluded=input_dto.excluded,
        )
        await self._diagnoses.add(diagnosis)
        self._uow.collect_events(diagnosis.pull_events())
        await self._uow.commit()

        return UpdateDifferentialDiagnosisOutput(
            differential_diagnosis_id=diagnosis.id, clinical_note_id=diagnosis.clinical_note_id
        )
