"""`CreatePatientHistory` — the module's only write operation: "History
records are immutable" / "Patient History is append-only" means there is
no update, no delete, no status transition — just this one creation
path.

"Only Approved Doctor Reviews may create Patient History" is checked by
fetching the review's own summary through `DoctorReviewQueryPort` and
comparing `review_status` against the literal string `"approved"`
(`DoctorReviewSummaryDTO.review_status` is a `ReviewStatus`, a
`StrEnum`, so this comparison is exact) rather than importing
`app.modules.doctor_review.domain.enums.ReviewStatus` — this module
never imports another module's `domain` package (see
`docs/backend-architecture/10_module_communication.md`), and the public
`DoctorReviewQueryPort` exposes no `is_approved()`/`is_rejected()`
boolean today (only a state-agnostic `is_editable()`, which cannot
distinguish `Approved` from `Rejected` — both make it `False`). Adding
one to `app.modules.doctor_review` was considered and rejected: it is
not "absolutely necessary" (rule 1) when the existing
`get_doctor_review_summary()` already carries everything needed.

Resolves `organization_id`/`patient_id`/`visit_id` from that same
summary — the identical "true by construction" technique every prior
child-document module uses — so "Patient and Organization consistency
must be enforced" is true unconditionally, not something validated after
the fact.

"Duplicate history records for the same source are prohibited" is
checked via `PatientHistoryRepository.get_by_reference()` before
construction — the identical "query first, then construct" technique
`app.modules.icd10_coding.application.use_cases.create_icd10_coding
.CreateICD10Coding` already uses for its own duplicate-code prevention —
and is additionally backed by a database-level partial unique index (see
`infrastructure/models.py`).

"Reference validation" and "Cross-module consistency" for
`(reference_type, reference_id)` are delegated to
`PatientHistoryReferenceValidator` — see that service's own docstring.
"""

from app.modules.doctor_review.public.interfaces import DoctorReviewQueryPort
from app.modules.patient_history.application.dto import (
    CreatePatientHistoryInput,
    CreatePatientHistoryOutput,
)
from app.modules.patient_history.application.services.patient_history_reference_validator import (
    PatientHistoryReferenceValidator,
)
from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.exceptions import (
    DoctorReviewNotApprovedError,
    DoctorReviewNotFoundError,
    DuplicatePatientHistoryError,
)
from app.modules.patient_history.domain.repositories import PatientHistoryRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase

_APPROVED_REVIEW_STATUS = "approved"


class CreatePatientHistory(UseCase[CreatePatientHistoryInput, CreatePatientHistoryOutput]):
    def __init__(
        self,
        *,
        patient_history_repository: PatientHistoryRepository,
        doctor_review_query_port: DoctorReviewQueryPort,
        reference_validator: PatientHistoryReferenceValidator,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._history = patient_history_repository
        self._doctor_reviews = doctor_review_query_port
        self._reference_validator = reference_validator
        self._uow = unit_of_work

    async def execute(self, input_dto: CreatePatientHistoryInput) -> CreatePatientHistoryOutput:
        review_summary = await self._doctor_reviews.get_doctor_review_summary(
            input_dto.doctor_review_id
        )
        if review_summary is None:
            raise DoctorReviewNotFoundError(input_dto.doctor_review_id)
        if review_summary.review_status != _APPROVED_REVIEW_STATUS:
            raise DoctorReviewNotApprovedError(input_dto.doctor_review_id)

        existing = await self._history.get_by_reference(
            input_dto.reference_type, input_dto.reference_id
        )
        if existing is not None:
            raise DuplicatePatientHistoryError(
                input_dto.reference_type.value, input_dto.reference_id
            )

        await self._reference_validator.validate(
            reference_type=input_dto.reference_type,
            reference_id=input_dto.reference_id,
            doctor_review_summary=review_summary,
        )

        history = PatientHistory.create(
            organization_id=review_summary.organization_id,
            patient_id=review_summary.patient_id,
            visit_id=review_summary.visit_id,
            doctor_review_id=input_dto.doctor_review_id,
            history_type=input_dto.history_type,
            reference_type=input_dto.reference_type,
            reference_id=input_dto.reference_id,
            encounter_date=input_dto.encounter_date,
            summary=input_dto.summary,
        )
        await self._history.add(history)
        self._uow.collect_events(history.pull_events())
        await self._uow.commit()

        return CreatePatientHistoryOutput(
            patient_history_id=history.id,
            organization_id=history.organization_id,
            patient_id=history.patient_id,
            history_type=history.history_type,
            reference_type=history.reference_type,
        )
