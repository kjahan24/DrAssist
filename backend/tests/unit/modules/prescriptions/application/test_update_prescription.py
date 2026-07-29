"""Unit tests for the `UpdatePrescription` use case — including both the
cross-module read-only enforcement (Clinical Note Signed/Locked) and the
own-aggregate read-only enforcement (Prescription already Final)."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.prescriptions.application.dto import UpdatePrescriptionInput
from app.modules.prescriptions.application.use_cases.update_prescription import UpdatePrescription
from app.modules.prescriptions.domain.entities import Prescription
from app.modules.prescriptions.domain.events import PrescriptionUpdated
from app.modules.prescriptions.domain.exceptions import (
    PrescriptionNotEditableError,
    PrescriptionNotFoundError,
)
from tests.unit.modules.prescriptions.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakePrescriptionRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> UpdatePrescriptionInput:
    defaults: dict[str, object] = {"prescription_id": uuid4()}
    defaults.update(overrides)
    return UpdatePrescriptionInput(**defaults)  # type: ignore[arg-type]


def _make_prescription(**overrides: object) -> Prescription:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "prescription_number": "RX-0001",
        "prescription_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return Prescription.create(**defaults)  # type: ignore[arg-type]


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
) -> UpdatePrescription:
    return UpdatePrescription(
        prescription_repository=prescription_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestUpdatePrescription:
    async def test_updates_fields_when_the_clinical_note_is_editable(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        await prescription_repository.add(prescription)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(prescription_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(prescription_id=prescription.id, notes="Revised instructions")
        )

        stored = await prescription_repository.get_by_id(output.prescription_id)
        assert stored is not None
        assert stored.notes == "Revised instructions"
        assert unit_of_work.committed is True
        assert any(isinstance(e, PrescriptionUpdated) for e in unit_of_work.published_events)

    async def test_unknown_prescription_raises(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(prescription_repository, unit_of_work, port)

        with pytest.raises(PrescriptionNotFoundError):
            await use_case.execute(_make_input(prescription_id=uuid4()))

    async def test_updating_once_the_clinical_note_is_signed_raises(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        await prescription_repository.add(prescription)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            },
            not_editable={clinical_note_id},
        )
        use_case = _use_case(prescription_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(prescription_id=prescription.id, notes="New"))

    async def test_updating_an_already_final_prescription_raises(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        prescription.finalize()
        await prescription_repository.add(prescription)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(prescription_repository, unit_of_work, port)

        with pytest.raises(PrescriptionNotEditableError):
            await use_case.execute(_make_input(prescription_id=prescription.id, notes="New"))

    async def test_unspecified_fields_are_left_unchanged(
        self, prescription_repository: FakePrescriptionRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id, notes="Original")
        await prescription_repository.add(prescription)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(prescription_repository, unit_of_work, port)

        await use_case.execute(
            _make_input(prescription_id=prescription.id, prescription_date=date(2026, 5, 1))
        )

        stored = await prescription_repository.get_by_id(prescription.id)
        assert stored is not None
        assert stored.notes == "Original"
        assert stored.prescription_date == date(2026, 5, 1)
