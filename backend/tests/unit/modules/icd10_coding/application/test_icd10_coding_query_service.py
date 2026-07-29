"""Unit tests for `ICD10CodingQueryService` — backs the module's public
`ICD10CodingQueryPort` facade."""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.application.services.icd10_coding_query_service import (
    ICD10CodingQueryService,
)
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource
from tests.unit.modules.icd10_coding.application.fakes import FakeICD10CodingRepository


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
def repo() -> FakeICD10CodingRepository:
    return FakeICD10CodingRepository()


@pytest.fixture
def service(repo: FakeICD10CodingRepository) -> ICD10CodingQueryService:
    return ICD10CodingQueryService(icd10_coding_repository=repo)


class TestICD10CodingExists:
    async def test_true_for_a_known_coding(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        coding = _make_coding()
        await repo.add(coding)
        assert await service.icd10_coding_exists(coding.id) is True

    async def test_false_for_an_unknown_coding(self, service: ICD10CodingQueryService) -> None:
        assert await service.icd10_coding_exists(uuid4()) is False


class TestIsEditable:
    async def test_true_while_pending(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        await repo.add(coding)
        assert await service.is_editable(coding.id) is True

    async def test_true_while_reviewed(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        coding = _make_coding(coding_source=CodingSource.PHYSICIAN)
        await repo.add(coding)
        assert await service.is_editable(coding.id) is True

    async def test_false_once_approved(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        coding = _make_coding()
        coding.approve()
        await repo.add(coding)
        assert await service.is_editable(coding.id) is False

    async def test_false_once_rejected(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        coding = _make_coding()
        coding.reject()
        await repo.add(coding)
        assert await service.is_editable(coding.id) is False

    async def test_false_for_an_unknown_coding(self, service: ICD10CodingQueryService) -> None:
        assert await service.is_editable(uuid4()) is False


class TestGetICD10CodingSummary:
    async def test_returns_summary_for_a_known_coding(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        coding = _make_coding(coding_notes="Confirmed via chest X-ray")
        await repo.add(coding)

        summary = await service.get_icd10_coding_summary(coding.id)

        assert summary is not None
        assert summary.icd10_coding_id == coding.id
        assert summary.organization_id == coding.organization_id
        assert summary.patient_id == coding.patient_id
        assert summary.visit_id == coding.visit_id
        assert summary.doctor_id == coding.doctor_id
        assert summary.icd10_code == "J18.9"
        assert summary.coding_notes == "Confirmed via chest X-ray"

    async def test_returns_none_for_an_unknown_coding(
        self, service: ICD10CodingQueryService
    ) -> None:
        assert await service.get_icd10_coding_summary(uuid4()) is None


class TestGetPrimaryICD10CodingForClinicalNote:
    async def test_returns_the_primary_coding(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        clinical_note_id = uuid4()
        await repo.add(
            _make_coding(clinical_note_id=clinical_note_id, icd10_code="R05", primary_code=False)
        )
        primary = _make_coding(
            clinical_note_id=clinical_note_id, icd10_code="J18.9", primary_code=True
        )
        await repo.add(primary)

        summary = await service.get_primary_icd10_coding_for_clinical_note(clinical_note_id)

        assert summary is not None
        assert summary.icd10_coding_id == primary.id

    async def test_returns_none_when_no_code_is_primary(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        clinical_note_id = uuid4()
        await repo.add(_make_coding(clinical_note_id=clinical_note_id))

        assert await service.get_primary_icd10_coding_for_clinical_note(clinical_note_id) is None


class TestListICD10CodingsForClinicalNote:
    async def test_returns_codes_scoped_to_the_clinical_note(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        clinical_note_id = uuid4()
        await repo.add(_make_coding(clinical_note_id=clinical_note_id, icd10_code="J18.9"))
        await repo.add(_make_coding(clinical_note_id=clinical_note_id, icd10_code="R05"))
        await repo.add(_make_coding(icd10_code="A00"))

        summaries = await service.list_icd10_codings_for_clinical_note(clinical_note_id)

        assert {s.icd10_code for s in summaries} == {"J18.9", "R05"}

    async def test_returns_empty_list_for_a_clinical_note_without_codes(
        self, service: ICD10CodingQueryService
    ) -> None:
        assert await service.list_icd10_codings_for_clinical_note(uuid4()) == []


class TestListICD10CodingsForPatient:
    async def test_returns_codes_scoped_to_the_patient(
        self, service: ICD10CodingQueryService, repo: FakeICD10CodingRepository
    ) -> None:
        patient_id = uuid4()
        await repo.add(_make_coding(patient_id=patient_id, icd10_code="J18.9"))
        await repo.add(_make_coding(icd10_code="R05"))

        summaries = await service.list_icd10_codings_for_patient(patient_id)

        assert [s.icd10_code for s in summaries] == ["J18.9"]

    async def test_returns_empty_list_for_a_patient_without_codes(
        self, service: ICD10CodingQueryService
    ) -> None:
        assert await service.list_icd10_codings_for_patient(uuid4()) == []
