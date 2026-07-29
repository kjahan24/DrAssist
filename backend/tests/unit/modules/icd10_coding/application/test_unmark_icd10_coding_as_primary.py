"""Unit tests for the `UnmarkICD10CodingAsPrimary` use case — the mirror
of `MarkICD10CodingAsPrimary`; demoting can never violate "only one
Primary per Clinical Note", so no sibling query is involved."""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.application.dto import UnmarkICD10CodingAsPrimaryInput
from app.modules.icd10_coding.application.use_cases.unmark_icd10_coding_as_primary import (
    UnmarkICD10CodingAsPrimary,
)
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource
from app.modules.icd10_coding.domain.events import ICD10CodingPrimaryChanged
from app.modules.icd10_coding.domain.exceptions import (
    ICD10CodingNotEditableError,
    ICD10CodingNotFoundError,
)
from tests.unit.modules.icd10_coding.application.fakes import (
    FakeICD10CodingRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UnmarkICD10CodingAsPrimaryInput:
    defaults: dict[str, object] = {"icd10_coding_id": uuid4()}
    defaults.update(overrides)
    return UnmarkICD10CodingAsPrimaryInput(**defaults)  # type: ignore[arg-type]


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
) -> UnmarkICD10CodingAsPrimary:
    return UnmarkICD10CodingAsPrimary(
        icd10_coding_repository=coding_repository, unit_of_work=unit_of_work
    )


class TestUnmarkICD10CodingAsPrimary:
    async def test_unmarks_a_primary_coding(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding(primary_code=True)
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        output = await use_case.execute(_make_input(icd10_coding_id=coding.id))

        assert output.primary_code is False
        stored = await coding_repository.get_by_id(coding.id)
        assert stored is not None
        assert stored.primary_code is False
        assert any(isinstance(e, ICD10CodingPrimaryChanged) for e in unit_of_work.published_events)

    async def test_unknown_coding_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotFoundError):
            await use_case.execute(_make_input(icd10_coding_id=uuid4()))

    async def test_unmarking_an_approved_coding_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding(primary_code=True)
        coding.approve()
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotEditableError):
            await use_case.execute(_make_input(icd10_coding_id=coding.id))
