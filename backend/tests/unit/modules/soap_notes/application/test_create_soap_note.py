"""Unit tests for the `CreateSOAPNote` use case, using in-memory fakes for
both this module's own repository and the Clinical Notes module's public
port."""

from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.soap_notes.application.dto import CreateSOAPNoteInput
from app.modules.soap_notes.application.use_cases.create_soap_note import CreateSOAPNote
from app.modules.soap_notes.domain.events import SOAPNoteCreated
from app.modules.soap_notes.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DuplicateSOAPNoteError,
)
from tests.unit.modules.soap_notes.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeSOAPNoteRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> CreateSOAPNoteInput:
    defaults: dict[str, object] = {"clinical_note_id": uuid4()}
    defaults.update(overrides)
    return CreateSOAPNoteInput(**defaults)  # type: ignore[arg-type]


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
) -> CreateSOAPNote:
    return CreateSOAPNote(
        soap_note_repository=soap_note_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestCreateSOAPNote:
    async def test_creates_a_soap_note_deriving_identity_from_the_clinical_note(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()
        summary = make_clinical_note_summary(
            clinical_note_id=clinical_note_id,
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, chief_complaint="Fever")
        )

        stored = await soap_note_repository.get_by_id(output.soap_note_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert stored.chief_complaint == "Fever"
        assert unit_of_work.committed is True
        assert any(isinstance(e, SOAPNoteCreated) for e in unit_of_work.published_events)

    async def test_unknown_clinical_note_raises(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotFoundError):
            await use_case.execute(_make_input(clinical_note_id=uuid4()))

    async def test_creating_against_a_signed_clinical_note_raises(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(
            existing_notes={clinical_note_id: summary}, not_editable={clinical_note_id}
        )
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

    async def test_a_second_soap_note_for_the_same_clinical_note_raises(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(soap_note_repository, unit_of_work, port)
        await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

        with pytest.raises(DuplicateSOAPNoteError):
            await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

    async def test_soap_notes_for_different_clinical_notes_are_both_allowed(
        self, soap_note_repository: FakeSOAPNoteRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_a = uuid4()
        clinical_note_b = uuid4()
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_a: make_clinical_note_summary(clinical_note_id=clinical_note_a),
                clinical_note_b: make_clinical_note_summary(clinical_note_id=clinical_note_b),
            }
        )
        use_case = _use_case(soap_note_repository, unit_of_work, port)

        await use_case.execute(_make_input(clinical_note_id=clinical_note_a))
        output_b = await use_case.execute(_make_input(clinical_note_id=clinical_note_b))

        stored_b = await soap_note_repository.get_by_id(output_b.soap_note_id)
        assert stored_b is not None
        assert stored_b.clinical_note_id == clinical_note_b
