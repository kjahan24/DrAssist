"""Unit tests for `PrescriptionQueryService` — backs the module's public
`PrescriptionQueryPort` facade."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.prescriptions.application.services.prescription_query_service import (
    PrescriptionQueryService,
)
from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.domain.enums import AdministrationRoute
from tests.unit.modules.prescriptions.application.fakes import (
    FakePrescriptionItemRepository,
    FakePrescriptionRepository,
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
def prescription_repo() -> FakePrescriptionRepository:
    return FakePrescriptionRepository()


@pytest.fixture
def item_repo() -> FakePrescriptionItemRepository:
    return FakePrescriptionItemRepository()


@pytest.fixture
def service(
    prescription_repo: FakePrescriptionRepository, item_repo: FakePrescriptionItemRepository
) -> PrescriptionQueryService:
    return PrescriptionQueryService(
        prescription_repository=prescription_repo, prescription_item_repository=item_repo
    )


class TestPrescriptionExistsForClinicalNote:
    async def test_true_for_a_known_clinical_note(
        self, service: PrescriptionQueryService, prescription_repo: FakePrescriptionRepository
    ) -> None:
        prescription = _make_prescription()
        await prescription_repo.add(prescription)
        assert (
            await service.prescription_exists_for_clinical_note(prescription.clinical_note_id)
            is True
        )

    async def test_false_for_an_unknown_clinical_note(
        self, service: PrescriptionQueryService
    ) -> None:
        assert await service.prescription_exists_for_clinical_note(uuid4()) is False


class TestGetPrescriptionSummary:
    async def test_returns_summary_with_items_for_a_known_clinical_note(
        self,
        service: PrescriptionQueryService,
        prescription_repo: FakePrescriptionRepository,
        item_repo: FakePrescriptionItemRepository,
    ) -> None:
        prescription = _make_prescription(notes="Take with food")
        await prescription_repo.add(prescription)
        await item_repo.add(
            _make_item(prescription_id=prescription.id, medication_name="Amoxicillin")
        )
        await item_repo.add(
            _make_item(prescription_id=prescription.id, medication_name="Ibuprofen")
        )

        summary = await service.get_prescription_summary(prescription.clinical_note_id)

        assert summary is not None
        assert summary.prescription_id == prescription.id
        assert summary.organization_id == prescription.organization_id
        assert summary.patient_id == prescription.patient_id
        assert summary.visit_id == prescription.visit_id
        assert summary.doctor_id == prescription.doctor_id
        assert summary.notes == "Take with food"
        assert {i.medication_name for i in summary.items} == {"Amoxicillin", "Ibuprofen"}

    async def test_returns_summary_with_empty_items_when_none_added(
        self, service: PrescriptionQueryService, prescription_repo: FakePrescriptionRepository
    ) -> None:
        prescription = _make_prescription()
        await prescription_repo.add(prescription)

        summary = await service.get_prescription_summary(prescription.clinical_note_id)

        assert summary is not None
        assert summary.items == []

    async def test_returns_none_for_an_unknown_clinical_note(
        self, service: PrescriptionQueryService
    ) -> None:
        assert await service.get_prescription_summary(uuid4()) is None


class TestListPrescriptionsForPatient:
    async def test_returns_prescriptions_scoped_to_the_patient(
        self, service: PrescriptionQueryService, prescription_repo: FakePrescriptionRepository
    ) -> None:
        patient_id = uuid4()
        await prescription_repo.add(
            _make_prescription(patient_id=patient_id, prescription_number="RX-A")
        )
        await prescription_repo.add(_make_prescription(prescription_number="RX-B"))

        summaries = await service.list_prescriptions_for_patient(patient_id)

        assert [s.prescription_number for s in summaries] == ["RX-A"]

    async def test_returns_empty_list_for_a_patient_without_prescriptions(
        self, service: PrescriptionQueryService
    ) -> None:
        assert await service.list_prescriptions_for_patient(uuid4()) == []


class TestSearchPrescriptions:
    """Search & Filtering module — `PrescriptionQueryService
    .search_prescriptions`. The key behavior worth a dedicated unit test
    (beyond simple filter/DTO-mapping forwarding, already covered by
    `SqlAlchemyPrescriptionRepository`'s own integration tests) is that
    each result's embedded items are correctly grouped back to *its own*
    prescription — not mixed up across prescriptions — after being
    fetched in a single batched call."""

    async def test_embeds_each_prescriptions_own_items_only(
        self,
        service: PrescriptionQueryService,
        prescription_repo: FakePrescriptionRepository,
        item_repo: FakePrescriptionItemRepository,
    ) -> None:
        organization_id = uuid4()
        prescription_a = _make_prescription(
            organization_id=organization_id, prescription_number="RX-A"
        )
        prescription_b = _make_prescription(
            organization_id=organization_id, prescription_number="RX-B"
        )
        await prescription_repo.add(prescription_a)
        await prescription_repo.add(prescription_b)
        await item_repo.add(
            _make_item(prescription_id=prescription_a.id, medication_name="Amoxicillin")
        )
        await item_repo.add(
            _make_item(prescription_id=prescription_b.id, medication_name="Ibuprofen")
        )

        summaries, total = await service.search_prescriptions(organization_id=organization_id)

        assert total == 2
        by_number = {s.prescription_number: s for s in summaries}
        assert [i.medication_name for i in by_number["RX-A"].items] == ["Amoxicillin"]
        assert [i.medication_name for i in by_number["RX-B"].items] == ["Ibuprofen"]

    async def test_prescription_without_items_gets_an_empty_item_list(
        self,
        service: PrescriptionQueryService,
        prescription_repo: FakePrescriptionRepository,
    ) -> None:
        organization_id = uuid4()
        await prescription_repo.add(_make_prescription(organization_id=organization_id))

        summaries, _total = await service.search_prescriptions(organization_id=organization_id)

        assert summaries[0].items == []

    async def test_returns_empty_result_for_an_organization_with_no_prescriptions(
        self, service: PrescriptionQueryService
    ) -> None:
        summaries, total = await service.search_prescriptions(organization_id=uuid4())

        assert summaries == []
        assert total == 0
