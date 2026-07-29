"""Unit tests for `SOAPNoteQueryService` — backs the module's public
`SOAPNoteQueryPort` facade."""

from uuid import uuid4

import pytest

from app.modules.soap_notes.application.services.soap_note_query_service import (
    SOAPNoteQueryService,
)
from app.modules.soap_notes.domain.entities import SOAPNote
from tests.unit.modules.soap_notes.application.fakes import FakeSOAPNoteRepository


def _make_soap_note(**overrides: object) -> SOAPNote:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
    }
    defaults.update(overrides)
    return SOAPNote.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def soap_note_repo() -> FakeSOAPNoteRepository:
    return FakeSOAPNoteRepository()


@pytest.fixture
def service(soap_note_repo: FakeSOAPNoteRepository) -> SOAPNoteQueryService:
    return SOAPNoteQueryService(soap_note_repository=soap_note_repo)


class TestSOAPNoteExistsForClinicalNote:
    async def test_true_for_a_known_clinical_note(
        self, service: SOAPNoteQueryService, soap_note_repo: FakeSOAPNoteRepository
    ) -> None:
        soap_note = _make_soap_note()
        await soap_note_repo.add(soap_note)
        assert await service.soap_note_exists_for_clinical_note(soap_note.clinical_note_id) is True

    async def test_false_for_an_unknown_clinical_note(self, service: SOAPNoteQueryService) -> None:
        assert await service.soap_note_exists_for_clinical_note(uuid4()) is False


class TestGetSOAPNoteSummary:
    async def test_returns_summary_for_a_known_clinical_note(
        self, service: SOAPNoteQueryService, soap_note_repo: FakeSOAPNoteRepository
    ) -> None:
        soap_note = _make_soap_note(chief_complaint="Headache", plan="Rest and hydration")
        await soap_note_repo.add(soap_note)

        summary = await service.get_soap_note_summary(soap_note.clinical_note_id)

        assert summary is not None
        assert summary.soap_note_id == soap_note.id
        assert summary.organization_id == soap_note.organization_id
        assert summary.clinical_note_id == soap_note.clinical_note_id
        assert summary.patient_id == soap_note.patient_id
        assert summary.visit_id == soap_note.visit_id
        assert summary.doctor_id == soap_note.doctor_id
        assert summary.chief_complaint == "Headache"
        assert summary.plan == "Rest and hydration"

    async def test_returns_none_for_an_unknown_clinical_note(
        self, service: SOAPNoteQueryService
    ) -> None:
        assert await service.get_soap_note_summary(uuid4()) is None
