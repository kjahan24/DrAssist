"""Unit tests for the `FinalizePrescription` use case — including "A Final
Prescription must contain at least one Prescription Item", the one
invariant in this module that spans two separate aggregates."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.prescriptions.application.dto import FinalizePrescriptionInput
from app.modules.prescriptions.application.use_cases.finalize_prescription import (
    FinalizePrescription,
)
from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.domain.enums import AdministrationRoute, PrescriptionStatus
from app.modules.prescriptions.domain.events import PrescriptionFinalized
from app.modules.prescriptions.domain.exceptions import (
    PrescriptionNotEditableError,
    PrescriptionNotFoundError,
    PrescriptionRequiresAtLeastOneItemError,
)
from tests.unit.modules.prescriptions.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakePrescriptionItemRepository,
    FakePrescriptionRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


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


def _make_item(**overrides: object) -> PrescriptionItem:
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
    return PrescriptionItem.create(**defaults)  # type: ignore[arg-type]


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
) -> FinalizePrescription:
    return FinalizePrescription(
        prescription_repository=prescription_repository,
        prescription_item_repository=prescription_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestFinalizePrescription:
    async def test_finalizes_a_prescription_with_at_least_one_item(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        await prescription_repository.add(prescription)
        await prescription_item_repository.add(_make_item(prescription_id=prescription.id))
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(
            prescription_repository, prescription_item_repository, unit_of_work, port
        )

        output = await use_case.execute(FinalizePrescriptionInput(prescription_id=prescription.id))

        assert output.status is PrescriptionStatus.FINAL
        stored = await prescription_repository.get_by_id(prescription.id)
        assert stored is not None
        assert stored.status is PrescriptionStatus.FINAL
        assert unit_of_work.committed is True
        assert any(isinstance(e, PrescriptionFinalized) for e in unit_of_work.published_events)

    async def test_finalizing_without_any_items_raises(
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

        with pytest.raises(PrescriptionRequiresAtLeastOneItemError):
            await use_case.execute(FinalizePrescriptionInput(prescription_id=prescription.id))

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
            await use_case.execute(FinalizePrescriptionInput(prescription_id=uuid4()))

    async def test_finalizing_once_the_clinical_note_is_signed_raises(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        await prescription_repository.add(prescription)
        await prescription_item_repository.add(_make_item(prescription_id=prescription.id))
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
            await use_case.execute(FinalizePrescriptionInput(prescription_id=prescription.id))

    async def test_finalizing_an_already_final_prescription_raises(
        self,
        prescription_repository: FakePrescriptionRepository,
        prescription_item_repository: FakePrescriptionItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        prescription = _make_prescription(clinical_note_id=clinical_note_id)
        prescription.finalize()
        await prescription_repository.add(prescription)
        await prescription_item_repository.add(_make_item(prescription_id=prescription.id))
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(
            prescription_repository, prescription_item_repository, unit_of_work, port
        )

        with pytest.raises(PrescriptionNotEditableError):
            await use_case.execute(FinalizePrescriptionInput(prescription_id=prescription.id))
