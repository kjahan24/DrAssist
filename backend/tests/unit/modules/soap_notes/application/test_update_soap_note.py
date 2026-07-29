"""Unit tests for the `UpdateSOAPNote` use case — including the read-only
enforcement for Signed/Locked Clinical Notes that
`SOAPNote.update_details()` itself deliberately does not perform (see
`app/modules/soap_notes/domain/entities.py`)."""

from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.soap_notes.application.dto import UpdateSOAPNoteInput
from app.modules.soap_notes.application.use_cases.update_soap_note import UpdateSOAPNote
from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.domain.events import SOAPNoteUpdated
from app.modules.soap_notes.domain.exceptions import SOAPNoteNotFoundError
from tests.unit.modules.soap_notes.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeSOAPNoteRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> UpdateSOAPNoteInput:
    defaults: dict[str, object] = {"soap_note_id": uuid4()}
    defaults.update(overrides)
    return UpdateSOAPNoteInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def soap_note_repository() -> FakeSOAPNoteRepository:
    return FakeSOAPNoteRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    soap_note_repository: FakeSOAPNoteRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
) -> UpdateSOAPNote:
    return UpdateSOAPNote(
        soap_note_repository=soap_note_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestUpdateSOAPNote:
    async def test_updates_fields_when_the_clinical_note_is_editable(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        soap_note = SOAPNote.create(
            organization_id=uuid4(),
            clinical_note_id=clinical_note_id,
            patient_id=uuid4(),
            visit_id=uuid4(),
            doctor_id=uuid4(),
        )
        await soap_note_repository.add(soap_note)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(soap_note_id=soap_note.id, assessment="Improving")
        )

        stored = await soap_note_repository.get_by_id(output.soap_note_id)
        assert stored is not None
        assert stored.assessment == "Improving"
        assert unit_of_work.committed is True
        assert any(isinstance(e, SOAPNoteUpdated) for e in unit_of_work.published_events)

    async def test_unknown_soap_note_raises(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        with pytest.raises(SOAPNoteNotFoundError):
            await use_case.execute(_make_input(soap_note_id=uuid4()))

    async def test_updating_once_the_clinical_note_is_signed_raises(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        soap_note = SOAPNote.create(
            organization_id=uuid4(),
            clinical_note_id=clinical_note_id,
            patient_id=uuid4(),
            visit_id=uuid4(),
            doctor_id=uuid4(),
        )
        await soap_note_repository.add(soap_note)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            },
            not_editable={clinical_note_id},
        )
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(soap_note_id=soap_note.id, plan="New plan"))

    async def test_unspecified_fields_are_left_unchanged(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        soap_note = SOAPNote.create(
            organization_id=uuid4(),
            clinical_note_id=clinical_note_id,
            patient_id=uuid4(),
            visit_id=uuid4(),
            doctor_id=uuid4(),
            assessment="Stable",
        )
        await soap_note_repository.add(soap_note)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        await use_case.execute(_make_input(soap_note_id=soap_note.id, plan="Follow up in 1 week"))

        stored = await soap_note_repository.get_by_id(soap_note.id)
        assert stored is not None
        assert stored.assessment == "Stable"
        assert stored.plan == "Follow up in 1 week"
