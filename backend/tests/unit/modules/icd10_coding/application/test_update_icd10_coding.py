"""Unit tests for the `UpdateICD10Coding` use case. No cross-module port
is constructed at all — see `domain/entities.py` for why this module
never checks the linked clinical note/differential diagnosis
editability."""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.application.dto import UpdateICD10CodingInput
from app.modules.icd10_coding.application.use_cases.update_icd10_coding import (
    UpdateICD10Coding,
)
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource
from app.modules.icd10_coding.domain.events import ICD10CodingUpdated
from app.modules.icd10_coding.domain.exceptions import (
    ICD10CodingNotEditableError,
    ICD10CodingNotFoundError,
)
from tests.unit.modules.icd10_coding.application.fakes import (
    FakeICD10CodingRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateICD10CodingInput:
    defaults: dict[str, object] = {"icd10_coding_id": uuid4()}
    defaults.update(overrides)
    return UpdateICD10CodingInput(**defaults)  # type: ignore[arg-type]


def _make_coding(**overrides: object) -> ICD10Coding:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "icd10_code": "J18.9",
        "diagnosis_title": "Pneumonia, unspecified organism",
        "coding_source": CodingSource.AI,
    }
    defaults.update(overrides)
    return ICD10Coding.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def coding_repository() -> FakeICD10CodingRepository:
    return FakeICD10CodingRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
) -> UpdateICD10Coding:
    return UpdateICD10Coding(icd10_coding_repository=coding_repository, unit_of_work=unit_of_work)


class TestUpdateICD10Coding:
    async def test_updates_fields_while_editable(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding()
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        output = await use_case.execute(
            _make_input(icd10_coding_id=coding.id, diagnosis_title="Bacterial pneumonia")
        )

        stored = await coding_repository.get_by_id(output.icd10_coding_id)
        assert stored is not None
        assert stored.diagnosis_title == "Bacterial pneumonia"
        assert unit_of_work.committed is True
        assert any(isinstance(e, ICD10CodingUpdated) for e in unit_of_work.published_events)

    async def test_unknown_coding_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotFoundError):
            await use_case.execute(_make_input(icd10_coding_id=uuid4()))

    async def test_updating_an_approved_coding_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding()
        coding.approve()
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotEditableError):
            await use_case.execute(
                _make_input(icd10_coding_id=coding.id, diagnosis_title="New title")
            )
