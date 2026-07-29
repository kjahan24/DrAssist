"""Unit tests for the `UpdateDifferentialDiagnosis` use case. No
cross-module port is constructed at all — see `domain/entities.py` for
why this module never checks the linked clinical note/reasoning
editability."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis.application.dto import (
    UpdateDifferentialDiagnosisInput,
)
from app.modules.differential_diagnosis.application.use_cases.update_differential_diagnosis import (  # noqa: E501
    UpdateDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource
from app.modules.differential_diagnosis.domain.events import DifferentialDiagnosisUpdated
from app.modules.differential_diagnosis.domain.exceptions import (
    DifferentialDiagnosisNotEditableError,
    DifferentialDiagnosisNotFoundError,
)
from tests.unit.modules.differential_diagnosis.application.fakes import (
    FakeDifferentialDiagnosisRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateDifferentialDiagnosisInput:
    defaults: dict[str, object] = {"differential_diagnosis_id": uuid4()}
    defaults.update(overrides)
    return UpdateDifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


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
) -> UpdateDifferentialDiagnosis:
    return UpdateDifferentialDiagnosis(
        differential_diagnosis_repository=diagnosis_repository, unit_of_work=unit_of_work
    )


class TestUpdateDifferentialDiagnosis:
    async def test_updates_fields_while_editable(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        diagnosis = _make_diagnosis()
        await diagnosis_repository.add(diagnosis)
        use_case = _use_case(diagnosis_repository, unit_of_work)

        output = await use_case.execute(
            _make_input(differential_diagnosis_id=diagnosis.id, diagnosis_name="Atypical pneumonia")
        )

        stored = await diagnosis_repository.get_by_id(output.differential_diagnosis_id)
        assert stored is not None
        assert stored.diagnosis_name == "Atypical pneumonia"
        assert unit_of_work.committed is True
        assert any(
            isinstance(e, DifferentialDiagnosisUpdated) for e in unit_of_work.published_events
        )

    async def test_unknown_diagnosis_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(diagnosis_repository, unit_of_work)

        with pytest.raises(DifferentialDiagnosisNotFoundError):
            await use_case.execute(_make_input(differential_diagnosis_id=uuid4()))

    async def test_updating_an_approved_diagnosis_raises(
        self,
        diagnosis_repository: FakeDifferentialDiagnosisRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.approve()
        await diagnosis_repository.add(diagnosis)
        use_case = _use_case(diagnosis_repository, unit_of_work)

        with pytest.raises(DifferentialDiagnosisNotEditableError):
            await use_case.execute(
                _make_input(differential_diagnosis_id=diagnosis.id, diagnosis_name="New")
            )
