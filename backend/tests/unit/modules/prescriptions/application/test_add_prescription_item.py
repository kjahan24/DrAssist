"""Unit tests for the `AddPrescriptionItem` use case."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.prescriptions.application.dto import AddPrescriptionItemInput
from app.modules.prescriptions.application.use_cases.add_prescription_item import (
    AddPrescriptionItem,
)
from app.modules.prescriptions.domain.entities import Prescription
from app.modules.prescriptions.domain.enums import AdministrationRoute
from app.modules.prescriptions.domain.events import PrescriptionItemAdded
from app.modules.prescriptions.domain.exceptions import (
    PrescriptionNotEditableError,
    PrescriptionNotFoundError,
)
from tests.unit.modules.prescriptions.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakePrescriptionItemRepository,
    FakePrescriptionRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> AddPrescriptionItemInput:
    defaults: dict[str, object] = {
        "prescription_id": uuid4(),
        "medication_name": "Amoxicillin",
        "strength": "500mg",
        "dosage": "1",
        "dosage_unit": "tablet",
        "frequency": "three times daily",
        "route": AdministrationRoute.ORAL,
        "duration": "7",
        "duration_unit": "days",
        "quantity": "21",
    }
    defaults.update(overrides)
    return AddPrescriptionItemInput(**defaults)  # type: ignore[arg-type]


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
def prescription_item_repository() -> FakePrescriptionItemRepository:
    return FakePrescriptionItemRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    prescription_repository: FakePrescriptionRepository,
    prescription_item_repository: FakePrescriptionItemRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
) -> AddPrescriptionItem:
    return AddPrescriptionItem(
        prescription_repository=prescription_repository,
        prescription_item_repository=prescription_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestAddPrescriptionItem:
    async def test_adds_an_item_owned_by_the_given_prescription(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        await prescription_repository.add(prescription)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(
            prescription_repository, prescription_item_repository, unit_of_work, port
        )

        output = await use_case.execute(
            _make_input(prescription_id=prescription.id, medication_name="Ibuprofen")
        )

        assert output.prescription_id == prescription.id
        stored = await prescription_item_repository.get_by_id(output.prescription_item_id)
        assert stored is not None
        assert stored.prescription_id == prescription.id
        assert stored.medication_name == "Ibuprofen"
        assert unit_of_work.committed is True
        assert any(isinstance(e, PrescriptionItemAdded) for e in unit_of_work.published_events)

    async def test_unknown_prescription_raises(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(
            prescription_repository, prescription_item_repository, unit_of_work, port
        )

        with pytest.raises(PrescriptionNotFoundError):
            await use_case.execute(_make_input(prescription_id=uuid4()))

    async def test_adding_to_an_already_final_prescription_raises(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
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
        use_case = _use_case(
            prescription_repository, prescription_item_repository, unit_of_work, port
        )

        with pytest.raises(PrescriptionNotEditableError):
            await use_case.execute(_make_input(prescription_id=prescription.id))

    async def test_adding_once_the_clinical_note_is_signed_raises(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
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
        use_case = _use_case(
            prescription_repository, prescription_item_repository, unit_of_work, port
        )

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(prescription_id=prescription.id))

    async def test_multiple_items_can_be_added_to_the_same_prescription(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        await prescription_repository.add(prescription)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(
            prescription_repository, prescription_item_repository, unit_of_work, port
        )

        await use_case.execute(
            _make_input(prescription_id=prescription.id, medication_name="Amoxicillin")
        )
        await use_case.execute(
            _make_input(prescription_id=prescription.id, medication_name="Ibuprofen")
        )

        items = await prescription_item_repository.list_by_prescription(prescription.id)
        assert {i.medication_name for i in items} == {"Amoxicillin", "Ibuprofen"}
