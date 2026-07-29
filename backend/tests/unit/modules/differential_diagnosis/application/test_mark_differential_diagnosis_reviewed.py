"""Unit tests for the `MarkDifferentialDiagnosisReviewed` use case."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis.application.dto import (
    MarkDifferentialDiagnosisReviewedInput,
)
from app.modules.differential_diagnosis.application.use_cases.mark_differential_diagnosis_reviewed import (  # noqa: E501
    MarkDifferentialDiagnosisReviewed,
)
from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus
from app.modules.differential_diagnosis.domain.exceptions import (
    DifferentialDiagnosisNotFoundError,
    ReviewRequiresPendingStatusError,
)
from tests.unit.modules.differential_diagnosis.application.fakes import (
    FakeDifferentialDiagnosisRepository,
    FakeUnitOfWork,
)


def _make_diagnosis(**overrides: object) -> DifferentialDiagnosis:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "diagnosis_name": "Community-acquired pneumonia",
        "diagnosis_source": DiagnosisSource.AI,
        "ranking": 1,
    }
    defaults.update(overrides)
    return DifferentialDiagnosis.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def diagnosis_repository() -> FakeDifferentialDiagnosisRepository:
    return FakeDifferentialDiagnosisRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    diagnosis_repository: FakeDifferentialDiagnosisRepository, unit_of_work: FakeUnitOfWork
) -> MarkDifferentialDiagnosisReviewed:
    return MarkDifferentialDiagnosisReviewed(
        differential_diagnosis_repository=diagnosis_repository, unit_of_work=unit_of_work
    )


class TestMarkDifferentialDiagnosisReviewed:
    async def test_marks_a_pending_diagnosis_as_reviewed(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        await diagnosis_repository.add(diagnosis)
        use_case = _use_case(diagnosis_repository, unit_of_work)

        output = await use_case.execute(
            MarkDifferentialDiagnosisReviewedInput(differential_diagnosis_id=diagnosis.id)
        )

        assert output.review_status is ReviewStatus.REVIEWED
        assert unit_of_work.committed is True

    async def test_marking_an_already_reviewed_diagnosis_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.PHYSICIAN)
        await diagnosis_repository.add(diagnosis)
        use_case = _use_case(diagnosis_repository, unit_of_work)

        with pytest.raises(ReviewRequiresPendingStatusError):
            await use_case.execute(
                MarkDifferentialDiagnosisReviewedInput(differential_diagnosis_id=diagnosis.id)
            )

    async def test_unknown_diagnosis_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(diagnosis_repository, unit_of_work)

        with pytest.raises(DifferentialDiagnosisNotFoundError):
            await use_case.execute(
                MarkDifferentialDiagnosisReviewedInput(differential_diagnosis_id=uuid4())
            )
