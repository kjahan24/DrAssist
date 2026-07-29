"""Unit tests for the `RejectDifferentialDiagnosis` use case."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis.application.dto import (
    RejectDifferentialDiagnosisInput,
)
from app.modules.differential_diagnosis.application.use_cases.reject_differential_diagnosis import (  # noqa: E501
    RejectDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus
from app.modules.differential_diagnosis.domain.exceptions import (
    DifferentialDiagnosisNotEditableError,
    DifferentialDiagnosisNotFoundError,
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
) -> RejectDifferentialDiagnosis:
    return RejectDifferentialDiagnosis(
        differential_diagnosis_repository=diagnosis_repository, unit_of_work=unit_of_work
    )


class TestRejectDifferentialDiagnosis:
    async def test_rejects_a_pending_diagnosis(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        await diagnosis_repository.add(diagnosis)
        use_case = _use_case(diagnosis_repository, unit_of_work)

        output = await use_case.execute(
            RejectDifferentialDiagnosisInput(differential_diagnosis_id=diagnosis.id)
        )

        assert output.review_status is ReviewStatus.REJECTED
        assert unit_of_work.committed is True

    async def test_rejecting_an_already_rejected_diagnosis_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.reject()
        await diagnosis_repository.add(diagnosis)
        use_case = _use_case(diagnosis_repository, unit_of_work)

        with pytest.raises(DifferentialDiagnosisNotEditableError):
            await use_case.execute(
                RejectDifferentialDiagnosisInput(differential_diagnosis_id=diagnosis.id)
            )

    async def test_unknown_diagnosis_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(diagnosis_repository, unit_of_work)

        with pytest.raises(DifferentialDiagnosisNotFoundError):
            await use_case.execute(
                RejectDifferentialDiagnosisInput(differential_diagnosis_id=uuid4())
            )
