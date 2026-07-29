"""Unit tests for the `CreatePrescription` use case, using in-memory
fakes for both this module's own repository and the Clinical Notes
module's public port."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.prescriptions.application.dto import CreatePrescriptionInput
from app.modules.prescriptions.application.use_cases.create_prescription import CreatePrescription
from app.modules.prescriptions.domain.events import PrescriptionCreated
from app.modules.prescriptions.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DuplicatePrescriptionError,
    DuplicatePrescriptionNumberError,
)
from tests.unit.modules.prescriptions.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakePrescriptionRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> CreatePrescriptionInput:
    defaults: dict[str, object] = {
        "clinical_note_id": uuid4(),
        "prescription_number": "RX-0001",
        "prescription_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return CreatePrescriptionInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def prescription_repository() -> FakePrescriptionRepository:
    return FakePrescriptionRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    prescription_repository: FakePrescriptionRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
) -> CreatePrescription:
    return CreatePrescription(
        prescription_repository=prescription_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestCreatePrescription:
    async def test_creates_a_prescription_deriving_identity_from_the_clinical_note(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
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
        use_case = _use_case(prescription_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, notes="Take after meals")
        )

        stored = await prescription_repository.get_by_id(output.prescription_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert stored.notes == "Take after meals"
        assert unit_of_work.committed is True
        assert any(isinstance(e, PrescriptionCreated) for e in unit_of_work.published_events)

    async def test_unknown_clinical_note_raises(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(prescription_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotFoundError):
            await use_case.execute(_make_input(clinical_note_id=uuid4()))

    async def test_creating_against_a_signed_clinical_note_raises(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(
            existing_notes={clinical_note_id: summary}, not_editable={clinical_note_id}
        )
        use_case = _use_case(prescription_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

    async def test_a_second_prescription_for_the_same_clinical_note_raises(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(prescription_repository, unit_of_work, port)
        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, prescription_number="RX-A")
        )

        with pytest.raises(DuplicatePrescriptionError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_id, prescription_number="RX-B")
            )

    async def test_duplicate_prescription_number_across_different_notes_raises(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_a = uuid4()
        clinical_note_b = uuid4()
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_a: make_clinical_note_summary(clinical_note_id=clinical_note_a),
                clinical_note_b: make_clinical_note_summary(clinical_note_id=clinical_note_b),
            }
        )
        use_case = _use_case(prescription_repository, unit_of_work, port)
        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_a, prescription_number="RX-SHARED")
        )

        with pytest.raises(DuplicatePrescriptionNumberError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_b, prescription_number="RX-SHARED")
            )
