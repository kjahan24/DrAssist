"""Unit tests for the `CreatePatientHistory` use case, using in-memory
fakes for this module's own repository, the Doctor Review module's
public port (the approval gate), and `PatientHistoryReferenceValidator`
(backed by its own fakes for the seven reference-checked ports)."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor_review.domain.enums import ReviewStatus as DoctorReviewStatus
from app.modules.patient_history.application.dto import CreatePatientHistoryInput
from app.modules.patient_history.application.services.patient_history_reference_validator import (
    PatientHistoryReferenceValidator,
)
from app.modules.patient_history.application.use_cases.create_patient_history import (
    CreatePatientHistory,
)
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from app.modules.patient_history.domain.events import PatientHistoryCreated
from app.modules.patient_history.domain.exceptions import (
    DoctorReviewNotApprovedError,
    DoctorReviewNotFoundError,
    DuplicatePatientHistoryError,
    ReferenceNotFoundError,
)
from tests.unit.modules.patient_history.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeDifferentialDiagnosisQueryPort,
    FakeDoctorReviewQueryPort,
    FakeICD10CodingQueryPort,
    FakeLabOrderQueryPort,
    FakeLabResultQueryPort,
    FakePatientHistoryRepository,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    FakeUnitOfWork,
    make_clinical_note_summary,
    make_doctor_review_summary,
)


def _make_input(**overrides: object) -> CreatePatientHistoryInput:
    defaults: dict[str, object] = {
        "doctor_review_id": uuid4(),
        "history_type": HistoryType.CLINICAL_NOTE,
        "reference_type": ReferenceType.CLINICAL_NOTE,
        "reference_id": uuid4(),
        "encounter_date": date(2026, 1, 1),
        "summary": "Initial encounter note",
    }
    defaults.update(overrides)
    return CreatePatientHistoryInput(**defaults)  # type: ignore[arg-type]


def _validator(**ports: object) -> PatientHistoryReferenceValidator:
    defaults: dict[str, object] = {
        "clinical_note_query_port": FakeClinicalNoteQueryPort(),
        "soap_note_query_port": FakeSOAPNoteQueryPort(),
        "prescription_query_port": FakePrescriptionQueryPort(),
        "lab_order_query_port": FakeLabOrderQueryPort(),
        "lab_result_query_port": FakeLabResultQueryPort(),
        "differential_diagnosis_query_port": FakeDifferentialDiagnosisQueryPort(),
        "icd10_coding_query_port": FakeICD10CodingQueryPort(),
    }
    defaults.update(ports)
    return PatientHistoryReferenceValidator(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def history_repository() -> FakePatientHistoryRepository:
    return FakePatientHistoryRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    history_repository: FakePatientHistoryRepository,
    unit_of_work: FakeUnitOfWork,
    doctor_review_query_port: FakeDoctorReviewQueryPort,
    reference_validator: PatientHistoryReferenceValidator | None = None,
) -> CreatePatientHistory:
    return CreatePatientHistory(
        patient_history_repository=history_repository,
        doctor_review_query_port=doctor_review_query_port,
        reference_validator=reference_validator or _validator(),
        unit_of_work=unit_of_work,
    )


class TestCreatePatientHistory:
    async def test_creates_history_from_an_approved_review(
        self, history_repository: FakePatientHistoryRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_review_id = uuid4()
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        clinical_note_id = uuid4()
        review = make_doctor_review_summary(
            doctor_review_id=doctor_review_id,
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            clinical_note_id=clinical_note_id,
            review_status=DoctorReviewStatus.APPROVED,
        )
        review_port = FakeDoctorReviewQueryPort(existing_reviews={doctor_review_id: review})
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(
            history_repository,
            unit_of_work,
            review_port,
            _validator(clinical_note_query_port=note_port),
        )

        output = await use_case.execute(
            _make_input(doctor_review_id=doctor_review_id, reference_id=clinical_note_id)
        )

        assert output.organization_id == organization_id
        assert output.patient_id == patient_id
        stored = await history_repository.get_by_id(output.patient_history_id)
        assert stored is not None
        assert stored.visit_id == visit_id
        assert stored.doctor_review_id == doctor_review_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, PatientHistoryCreated) for e in unit_of_work.published_events)

    async def test_unknown_doctor_review_raises(
        self, history_repository: FakePatientHistoryRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review_port = FakeDoctorReviewQueryPort()
        use_case = _use_case(history_repository, unit_of_work, review_port)

        with pytest.raises(DoctorReviewNotFoundError):
            await use_case.execute(_make_input(doctor_review_id=uuid4()))

    async def test_pending_review_is_rejected(
        self, history_repository: FakePatientHistoryRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_review_id = uuid4()
        review = make_doctor_review_summary(
            doctor_review_id=doctor_review_id, review_status=DoctorReviewStatus.PENDING
        )
        review_port = FakeDoctorReviewQueryPort(existing_reviews={doctor_review_id: review})
        use_case = _use_case(history_repository, unit_of_work, review_port)

        with pytest.raises(DoctorReviewNotApprovedError):
            await use_case.execute(_make_input(doctor_review_id=doctor_review_id))

    async def test_rejected_review_is_rejected(
        self, history_repository: FakePatientHistoryRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_review_id = uuid4()
        review = make_doctor_review_summary(
            doctor_review_id=doctor_review_id, review_status=DoctorReviewStatus.REJECTED
        )
        review_port = FakeDoctorReviewQueryPort(existing_reviews={doctor_review_id: review})
        use_case = _use_case(history_repository, unit_of_work, review_port)

        with pytest.raises(DoctorReviewNotApprovedError):
            await use_case.execute(_make_input(doctor_review_id=doctor_review_id))

    async def test_returned_for_revision_review_is_rejected(
        self, history_repository: FakePatientHistoryRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_review_id = uuid4()
        review = make_doctor_review_summary(
            doctor_review_id=doctor_review_id,
            review_status=DoctorReviewStatus.RETURNED_FOR_REVISION,
        )
        review_port = FakeDoctorReviewQueryPort(existing_reviews={doctor_review_id: review})
        use_case = _use_case(history_repository, unit_of_work, review_port)

        with pytest.raises(DoctorReviewNotApprovedError):
            await use_case.execute(_make_input(doctor_review_id=doctor_review_id))

    async def test_duplicate_history_for_the_same_source_raises(
        self, history_repository: FakePatientHistoryRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_review_id = uuid4()
        clinical_note_id = uuid4()
        review = make_doctor_review_summary(
            doctor_review_id=doctor_review_id, clinical_note_id=clinical_note_id
        )
        review_port = FakeDoctorReviewQueryPort(existing_reviews={doctor_review_id: review})
        note_port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        validator = _validator(clinical_note_query_port=note_port)
        use_case = _use_case(history_repository, unit_of_work, review_port, validator)
        input_dto = _make_input(doctor_review_id=doctor_review_id, reference_id=clinical_note_id)
        await use_case.execute(input_dto)

        with pytest.raises(DuplicatePatientHistoryError):
            await use_case.execute(input_dto)

    async def test_unresolvable_reference_raises(
        self, history_repository: FakePatientHistoryRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_review_id = uuid4()
        review = make_doctor_review_summary(doctor_review_id=doctor_review_id)
        review_port = FakeDoctorReviewQueryPort(existing_reviews={doctor_review_id: review})
        use_case = _use_case(history_repository, unit_of_work, review_port)

        with pytest.raises(ReferenceNotFoundError):
            await use_case.execute(
                _make_input(doctor_review_id=doctor_review_id, reference_id=uuid4())
            )
