"""Unit tests for the `CreateDoctorReview` use case, using in-memory
fakes for this module's own repository, the Clinical Notes module's
public port, and `DoctorReviewConsistencyService` (backed by its own
fakes for the seven peer-module ports)."""

from uuid import uuid4

import pytest

from app.modules.doctor_review.application.dto import CreateDoctorReviewInput
from app.modules.doctor_review.application.services.doctor_review_consistency_service import (
    DoctorReviewConsistencyService,
)
from app.modules.doctor_review.application.use_cases.create_doctor_review import (
    CreateDoctorReview,
)
from app.modules.doctor_review.domain.enums import ReviewStatus
from app.modules.doctor_review.domain.events import DoctorReviewCreated
from app.modules.doctor_review.domain.exceptions import (
    ApprovedCategoryMissingRecordError,
    ClinicalNoteNotFoundError,
    DuplicateDoctorReviewError,
)
from tests.unit.modules.doctor_review.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeClinicalReasoningQueryPort,
    FakeDifferentialDiagnosisQueryPort,
    FakeDoctorReviewRepository,
    FakeICD10CodingQueryPort,
    FakeLabOrderQueryPort,
    FakeLabResultQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> CreateDoctorReviewInput:
    defaults: dict[str, object] = {"clinical_note_id": uuid4()}
    defaults.update(overrides)
    return CreateDoctorReviewInput(**defaults)  # type: ignore[arg-type]


def _consistency_service() -> DoctorReviewConsistencyService:
    return DoctorReviewConsistencyService(
        soap_note_query_port=FakeSOAPNoteQueryPort(),
        prescription_query_port=FakePrescriptionQueryPort(),
        lab_order_query_port=FakeLabOrderQueryPort(),
        lab_result_query_port=FakeLabResultQueryPort(),
        clinical_reasoning_query_port=FakeClinicalReasoningQueryPort(),
        differential_diagnosis_query_port=FakeDifferentialDiagnosisQueryPort(),
        icd10_coding_query_port=FakeICD10CodingQueryPort(),
    )


@pytest.fixture
def review_repository() -> FakeDoctorReviewRepository:
    return FakeDoctorReviewRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    review_repository: FakeDoctorReviewRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
    consistency_service: DoctorReviewConsistencyService | None = None,
) -> CreateDoctorReview:
    return CreateDoctorReview(
        doctor_review_repository=review_repository,
        clinical_note_query_port=clinical_note_query_port,
        consistency_service=consistency_service or _consistency_service(),
        unit_of_work=unit_of_work,
    )


class TestCreateDoctorReview:
    async def test_creates_review_starting_pending(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()
        summary = make_clinical_note_summary(
            clinical_note_id=clinical_note_id,
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(review_repository, unit_of_work, port)

        output = await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

        assert output.review_status is ReviewStatus.PENDING
        stored = await review_repository.get_by_id(output.doctor_review_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorReviewCreated) for e in unit_of_work.published_events)

    async def test_unknown_clinical_note_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(review_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotFoundError):
            await use_case.execute(_make_input(clinical_note_id=uuid4()))

    async def test_second_review_for_the_same_clinical_note_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(review_repository, unit_of_work, port)
        await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

        with pytest.raises(DuplicateDoctorReviewError):
            await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

    async def test_review_for_a_different_clinical_note_is_allowed(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        note_a = uuid4()
        note_b = uuid4()
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                note_a: make_clinical_note_summary(clinical_note_id=note_a),
                note_b: make_clinical_note_summary(clinical_note_id=note_b),
            }
        )
        use_case = _use_case(review_repository, unit_of_work, port)
        await use_case.execute(_make_input(clinical_note_id=note_a))

        output_b = await use_case.execute(_make_input(clinical_note_id=note_b))

        stored_b = await review_repository.get_by_id(output_b.doctor_review_id)
        assert stored_b is not None
        assert stored_b.clinical_note_id == note_b

    async def test_approved_category_with_no_backing_record_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(review_repository, unit_of_work, port)

        with pytest.raises(ApprovedCategoryMissingRecordError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_id, approved_soap_note=True)
            )

    async def test_approved_category_with_backing_record_is_accepted(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        consistency_service = DoctorReviewConsistencyService(
            soap_note_query_port=FakeSOAPNoteQueryPort(
                clinical_notes_with_soap_note={clinical_note_id}
            ),
            prescription_query_port=FakePrescriptionQueryPort(),
            lab_order_query_port=FakeLabOrderQueryPort(),
            lab_result_query_port=FakeLabResultQueryPort(),
            clinical_reasoning_query_port=FakeClinicalReasoningQueryPort(),
            differential_diagnosis_query_port=FakeDifferentialDiagnosisQueryPort(),
            icd10_coding_query_port=FakeICD10CodingQueryPort(),
        )
        use_case = _use_case(review_repository, unit_of_work, port, consistency_service)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, approved_soap_note=True)
        )

        stored = await review_repository.get_by_id(output.doctor_review_id)
        assert stored is not None
        assert stored.approved_soap_note is True

    async def test_approved_clinical_note_needs_no_backing_check(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(review_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, approved_clinical_note=True)
        )

        stored = await review_repository.get_by_id(output.doctor_review_id)
        assert stored is not None
        assert stored.approved_clinical_note is True
