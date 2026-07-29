"""Unit tests for the `MarkICD10CodingAsPrimary` use case — the only
place "only one ICD-10 code can be marked as Primary" is enforced,
since sibling rows are a different aggregate instance."""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.application.dto import MarkICD10CodingAsPrimaryInput
from app.modules.icd10_coding.application.use_cases.mark_icd10_coding_as_primary import (
    MarkICD10CodingAsPrimary,
)
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource
from app.modules.icd10_coding.domain.events import ICD10CodingPrimaryChanged
from app.modules.icd10_coding.domain.exceptions import (
    DuplicatePrimaryCodeError,
    ICD10CodingNotEditableError,
    ICD10CodingNotFoundError,
)
from tests.unit.modules.icd10_coding.application.fakes import (
    FakeICD10CodingRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> MarkICD10CodingAsPrimaryInput:
    defaults: dict[str, object] = {"icd10_coding_id": uuid4()}
    defaults.update(overrides)
    return MarkICD10CodingAsPrimaryInput(**defaults)  # type: ignore[arg-type]


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
) -> MarkICD10CodingAsPrimary:
    return MarkICD10CodingAsPrimary(
        icd10_coding_repository=coding_repository, unit_of_work=unit_of_work
    )


class TestMarkICD10CodingAsPrimary:
    async def test_marks_as_primary_when_no_sibling_is_primary(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding()
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        output = await use_case.execute(_make_input(icd10_coding_id=coding.id))

        assert output.primary_code is True
        stored = await coding_repository.get_by_id(coding.id)
        assert stored is not None
        assert stored.primary_code is True
        assert any(isinstance(e, ICD10CodingPrimaryChanged) for e in unit_of_work.published_events)

    async def test_unknown_coding_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotFoundError):
            await use_case.execute(_make_input(icd10_coding_id=uuid4()))

    async def test_promoting_when_a_sibling_is_already_primary_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        primary_coding = _make_coding(clinical_note_id=clinical_note_id, primary_code=True)
        other_coding = _make_coding(clinical_note_id=clinical_note_id, icd10_code="R05")
        await coding_repository.add(primary_coding)
        await coding_repository.add(other_coding)
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(DuplicatePrimaryCodeError):
            await use_case.execute(_make_input(icd10_coding_id=other_coding.id))

    async def test_re_promoting_the_already_primary_coding_is_idempotent(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding(primary_code=True)
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        output = await use_case.execute(_make_input(icd10_coding_id=coding.id))

        assert output.primary_code is True

    async def test_marking_an_approved_coding_as_primary_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding()
        coding.approve()
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotEditableError):
            await use_case.execute(_make_input(icd10_coding_id=coding.id))
