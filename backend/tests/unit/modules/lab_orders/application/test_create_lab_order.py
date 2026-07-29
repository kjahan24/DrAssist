"""Unit tests for the `CreateLabOrder` use case, using in-memory fakes for
both this module's own repository and the Clinical Notes module's public
port."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.lab_orders.application.dto import CreateLabOrderInput
from app.modules.lab_orders.application.use_cases.create_lab_order import CreateLabOrder
from app.modules.lab_orders.domain.events import LabOrderCreated
from app.modules.lab_orders.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DuplicateOrderNumberError,
)
from tests.unit.modules.lab_orders.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeLabOrderRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> CreateLabOrderInput:
    defaults: dict[str, object] = {
        "clinical_note_id": uuid4(),
        "order_number": "LAB-0001",
        "ordered_at": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return CreateLabOrderInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def lab_order_repository() -> FakeLabOrderRepository:
    return FakeLabOrderRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    lab_order_repository: FakeLabOrderRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
) -> CreateLabOrder:
    return CreateLabOrder(
        lab_order_repository=lab_order_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestCreateLabOrder:
    async def test_creates_a_lab_order_deriving_identity_from_the_clinical_note(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
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
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, notes="Fasting required")
        )

        stored = await lab_order_repository.get_by_id(output.lab_order_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert stored.notes == "Fasting required"
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabOrderCreated) for e in unit_of_work.published_events)

    async def test_unknown_clinical_note_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotFoundError):
            await use_case.execute(_make_input(clinical_note_id=uuid4()))

    async def test_creating_against_a_signed_clinical_note_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(
            existing_notes={clinical_note_id: summary}, not_editable={clinical_note_id}
        )
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(clinical_note_id=clinical_note_id))

    async def test_a_second_lab_order_for_the_same_clinical_note_is_allowed(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        summary = make_clinical_note_summary(clinical_note_id=clinical_note_id)
        port = FakeClinicalNoteQueryPort(existing_notes={clinical_note_id: summary})
        use_case = _use_case(lab_order_repository, unit_of_work, port)
        await use_case.execute(_make_input(clinical_note_id=clinical_note_id, order_number="LAB-A"))

        output_b = await use_case.execute(
            _make_input(clinical_note_id=clinical_note_id, order_number="LAB-B")
        )

        stored_b = await lab_order_repository.get_by_id(output_b.lab_order_id)
        assert stored_b is not None
        assert stored_b.clinical_note_id == clinical_note_id

    async def test_duplicate_order_number_across_different_notes_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_a = uuid4()
        clinical_note_b = uuid4()
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_a: make_clinical_note_summary(clinical_note_id=clinical_note_a),
                clinical_note_b: make_clinical_note_summary(clinical_note_id=clinical_note_b),
            }
        )
        use_case = _use_case(lab_order_repository, unit_of_work, port)
        await use_case.execute(
            _make_input(clinical_note_id=clinical_note_a, order_number="LAB-SHARED")
        )

        with pytest.raises(DuplicateOrderNumberError):
            await use_case.execute(
                _make_input(clinical_note_id=clinical_note_b, order_number="LAB-SHARED")
            )
