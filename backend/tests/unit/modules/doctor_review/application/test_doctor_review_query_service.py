"""Unit tests for `DoctorReviewQueryService` — backs the module's public
`DoctorReviewQueryPort` facade."""

from uuid import uuid4

import pytest

from app.modules.doctor_review.application.services.doctor_review_query_service import (
    DoctorReviewQueryService,
)
from app.modules.doctor_review.domain.entities import DoctorReview
from tests.unit.modules.doctor_review.application.fakes import FakeDoctorReviewRepository


def _make_review(**overrides: object) -> DoctorReview:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "clinical_note_id": uuid4(),
    }
    defaults.update(overrides)
    return DoctorReview.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeDoctorReviewRepository:
    return FakeDoctorReviewRepository()


@pytest.fixture
def service(repo: FakeDoctorReviewRepository) -> DoctorReviewQueryService:
    return DoctorReviewQueryService(doctor_review_repository=repo)


class TestDoctorReviewExists:
    async def test_true_for_a_known_review(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        review = _make_review()
        await repo.add(review)
        assert await service.doctor_review_exists(review.id) is True

    async def test_false_for_an_unknown_review(self, service: DoctorReviewQueryService) -> None:
        assert await service.doctor_review_exists(uuid4()) is False


class TestIsEditable:
    async def test_true_while_pending(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        review = _make_review()
        await repo.add(review)
        assert await service.is_editable(review.id) is True

    async def test_true_while_returned_for_revision(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        review = _make_review()
        review.return_for_revision()
        await repo.add(review)
        assert await service.is_editable(review.id) is True

    async def test_false_once_approved(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        review = _make_review()
        review.approve()
        await repo.add(review)
        assert await service.is_editable(review.id) is False

    async def test_false_once_rejected(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        review = _make_review()
        review.reject()
        await repo.add(review)
        assert await service.is_editable(review.id) is False

    async def test_false_for_an_unknown_review(self, service: DoctorReviewQueryService) -> None:
        assert await service.is_editable(uuid4()) is False


class TestGetDoctorReviewSummary:
    async def test_returns_summary_for_a_known_review(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        review = _make_review(review_comment="Looks complete", approved_soap_note=True)
        await repo.add(review)

        summary = await service.get_doctor_review_summary(review.id)

        assert summary is not None
        assert summary.doctor_review_id == review.id
        assert summary.organization_id == review.organization_id
        assert summary.patient_id == review.patient_id
        assert summary.visit_id == review.visit_id
        assert summary.doctor_id == review.doctor_id
        assert summary.review_comment == "Looks complete"
        assert summary.approved_soap_note is True

    async def test_returns_none_for_an_unknown_review(
        self, service: DoctorReviewQueryService
    ) -> None:
        assert await service.get_doctor_review_summary(uuid4()) is None


class TestGetDoctorReviewForClinicalNote:
    async def test_returns_the_review_for_that_clinical_note(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        clinical_note_id = uuid4()
        review = _make_review(clinical_note_id=clinical_note_id)
        await repo.add(review)

        summary = await service.get_doctor_review_for_clinical_note(clinical_note_id)

        assert summary is not None
        assert summary.doctor_review_id == review.id

    async def test_returns_none_for_a_clinical_note_without_a_review(
        self, service: DoctorReviewQueryService
    ) -> None:
        assert await service.get_doctor_review_for_clinical_note(uuid4()) is None


class TestListDoctorReviewsForPatient:
    async def test_returns_reviews_scoped_to_the_patient(
        self, service: DoctorReviewQueryService, repo: FakeDoctorReviewRepository
    ) -> None:
        patient_id = uuid4()
        await repo.add(_make_review(patient_id=patient_id))
        await repo.add(_make_review())

        summaries = await service.list_doctor_reviews_for_patient(patient_id)

        assert len(summaries) == 1
        assert summaries[0].patient_id == patient_id

    async def test_returns_empty_list_for_a_patient_without_reviews(
        self, service: DoctorReviewQueryService
    ) -> None:
        assert await service.list_doctor_reviews_for_patient(uuid4()) == []
