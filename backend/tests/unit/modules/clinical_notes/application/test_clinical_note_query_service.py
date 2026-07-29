"""Unit tests for `ClinicalNoteQueryService` — backs the module's public
`ClinicalNoteQueryPort` facade."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.application.services.clinical_note_query_service import (
    ClinicalNoteQueryService,
)
from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteType
from tests.unit.modules.clinical_notes.application.fakes import FakeClinicalNoteRepository


def _make_note(**overrides: object) -> ClinicalNote:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "note_number": "CN-0001",
        "note_type": ClinicalNoteType.INITIAL,
        "encounter_datetime": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return ClinicalNote.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def clinical_note_repo() -> FakeClinicalNoteRepository:
    return FakeClinicalNoteRepository()


@pytest.fixture
def service(clinical_note_repo: FakeClinicalNoteRepository) -> ClinicalNoteQueryService:
    return ClinicalNoteQueryService(clinical_note_repository=clinical_note_repo)


class TestClinicalNoteExists:
    async def test_true_for_a_known_note(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        note = _make_note()
        await clinical_note_repo.add(note)
        assert await service.clinical_note_exists(note.id) is True

    async def test_false_for_an_unknown_note(self, service: ClinicalNoteQueryService) -> None:
        assert await service.clinical_note_exists(uuid4()) is False


class TestGetClinicalNoteSummary:
    async def test_returns_summary_for_a_known_note(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        note = _make_note(note_number="CN-42")
        await clinical_note_repo.add(note)

        summary = await service.get_clinical_note_summary(note.id)

        assert summary is not None
        assert summary.note_number == "CN-42"
        assert summary.organization_id == note.organization_id
        assert summary.patient_id == note.patient_id
        assert summary.visit_id == note.visit_id
        assert summary.doctor_id == note.doctor_id

    async def test_returns_none_for_an_unknown_note(
        self, service: ClinicalNoteQueryService
    ) -> None:
        assert await service.get_clinical_note_summary(uuid4()) is None


class TestIsEditable:
    async def test_true_while_draft(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        note = _make_note()
        await clinical_note_repo.add(note)
        assert await service.is_editable(note.id) is True

    async def test_true_while_in_review(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        note = _make_note()
        note.submit_for_review()
        await clinical_note_repo.add(note)
        assert await service.is_editable(note.id) is True

    async def test_false_once_signed(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        await clinical_note_repo.add(note)
        assert await service.is_editable(note.id) is False

    async def test_false_once_locked(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        note.lock(locked_at=datetime(2026, 1, 1, 11, 0))
        await clinical_note_repo.add(note)
        assert await service.is_editable(note.id) is False

    async def test_false_for_an_unknown_note(self, service: ClinicalNoteQueryService) -> None:
        assert await service.is_editable(uuid4()) is False


class TestListClinicalNotesForVisit:
    async def test_returns_notes_scoped_to_the_visit(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        visit_id = uuid4()
        await clinical_note_repo.add(_make_note(visit_id=visit_id, note_number="CN-0001"))
        await clinical_note_repo.add(_make_note(note_number="CN-0002"))

        summaries = await service.list_clinical_notes_for_visit(visit_id)

        assert [s.note_number for s in summaries] == ["CN-0001"]

    async def test_returns_empty_list_for_a_visit_without_notes(
        self, service: ClinicalNoteQueryService
    ) -> None:
        assert await service.list_clinical_notes_for_visit(uuid4()) == []


class TestListClinicalNotesForPatient:
    async def test_returns_notes_scoped_to_the_patient(
        self, service: ClinicalNoteQueryService, clinical_note_repo: FakeClinicalNoteRepository
    ) -> None:
        patient_id = uuid4()
        await clinical_note_repo.add(_make_note(patient_id=patient_id, note_number="CN-0001"))
        await clinical_note_repo.add(_make_note(note_number="CN-0002"))

        summaries = await service.list_clinical_notes_for_patient(patient_id)

        assert [s.note_number for s in summaries] == ["CN-0001"]

    async def test_returns_empty_list_for_a_patient_without_notes(
        self, service: ClinicalNoteQueryService
    ) -> None:
        assert await service.list_clinical_notes_for_patient(uuid4()) == []
