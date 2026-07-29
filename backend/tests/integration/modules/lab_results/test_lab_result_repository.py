"""Integration tests for `SqlAlchemyLabResultRepository`, including the
FKs to `organizations`/`lab_orders`/`patients`/`patient_visits`/`doctors`,
the "at most one lab result per lab order" partial unique index, and the
"result_number is globally unique" partial unique index, against a real
PostgreSQL instance.

No `TestCheckConstraints` class here, matching
`tests.integration.modules.prescriptions.test_prescription_repository` —
like `prescriptions`, `lab_results` carries no `CHECK` constraints at all
(see `app/modules/lab_results/infrastructure/models.py` for why "a Final
Lab Result must contain at least one Lab Result Item" has no
database-level enforcement layer)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.lab_results._helpers import persist_full_chain, persist_lab_order

from app.modules.lab_results.domain.entities import LabResult
from app.modules.lab_results.domain.enums import LabResultStatus
from app.modules.lab_results.infrastructure.repositories import SqlAlchemyLabResultRepository


class TestLabResultRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-0001",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
            laboratory_name="Acme Labs",
            comments="Sample hemolyzed",
        )
        await repo.add(lab_result)
        await db_session.commit()

        reloaded = await repo.get_by_id(lab_result.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.lab_order_id == lab_order.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.result_number == "RES-0001"
        assert reloaded.reported_at == datetime(2026, 1, 2, 8, 0, tzinfo=UTC)
        assert reloaded.status is LabResultStatus.DRAFT
        assert reloaded.laboratory_name == "Acme Labs"
        assert reloaded.comments == "Sample hemolyzed"

    async def test_finalize_persists_status(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-0002",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        await db_session.commit()

        lab_result.finalize()
        await repo.add(lab_result)
        await db_session.commit()

        reloaded = await repo.get_by_id(lab_result.id)
        assert reloaded is not None
        assert reloaded.status is LabResultStatus.FINAL


class TestGetByLabOrderId:
    async def test_returns_the_matching_lab_result(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-0003",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        await db_session.commit()

        found = await repo.get_by_lab_order_id(lab_order.id)
        assert found is not None and found.id == lab_result.id

    async def test_returns_none_for_an_unknown_lab_order(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyLabResultRepository(db_session)
        assert await repo.get_by_lab_order_id(uuid4()) is None


class TestGetByResultNumber:
    async def test_returns_the_matching_lab_result(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-UNIQUE",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        await db_session.commit()

        found = await repo.get_by_result_number("RES-UNIQUE")
        assert found is not None and found.id == lab_result.id

    async def test_returns_none_for_an_unknown_number(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyLabResultRepository(db_session)
        assert await repo.get_by_result_number("does-not-exist") is None


class TestListByPatient:
    async def test_returns_results_scoped_to_the_patient_across_lab_orders(
        self, db_session: AsyncSession
    ) -> None:
        (
            organization,
            patient,
            doctor,
            visit,
            _note_a,
            lab_order_a,
            _item_a,
        ) = await persist_full_chain(db_session)
        lab_order_b = await persist_lab_order(
            db_session,
            organization_id=organization.id,
            clinical_note_id=_note_a.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        (
            _org2,
            other_patient,
            other_doctor,
            other_visit,
            other_note,
            other_order,
            _other_item,
        ) = await persist_full_chain(db_session)
        repo = SqlAlchemyLabResultRepository(db_session)

        await repo.add(
            LabResult.create(
                organization_id=organization.id,
                lab_order_id=lab_order_a.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                result_number="RES-PAT-A",
                reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            LabResult.create(
                organization_id=organization.id,
                lab_order_id=lab_order_b.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                result_number="RES-PAT-B",
                reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            LabResult.create(
                organization_id=_org2.id,
                lab_order_id=other_order.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_id=other_doctor.id,
                result_number="RES-PAT-OTHER",
                reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
            )
        )
        await db_session.commit()

        results = await repo.list_by_patient(patient.id)
        assert {r.result_number for r in results} == {"RES-PAT-A", "RES-PAT-B"}


class TestOneToOneUniqueness:
    async def test_a_second_lab_result_for_the_same_lab_order_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        first = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-FIRST",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(first)
        await db_session.commit()

        second = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-SECOND",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestResultNumberUniqueness:
    async def test_duplicate_result_number_across_different_orders_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note, lab_order_a, _item_a = await persist_full_chain(
            db_session
        )
        lab_order_b = await persist_lab_order(
            db_session,
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        repo = SqlAlchemyLabResultRepository(db_session)
        shared_number = "RES-SHARED"

        first = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order_a.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number=shared_number,
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(first)
        await db_session.commit()

        second = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order_b.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number=shared_number,
            reported_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestLabResultRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=uuid4(),
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-ORPHAN-ORG",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_lab_order_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _note, _lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-ORPHAN-ORDER",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            result_number="RES-ORPHAN-PATIENT",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            result_number="RES-ORPHAN-VISIT",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, _note, lab_order, _item = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabResultRepository(db_session)

        lab_result = LabResult.create(
            organization_id=organization.id,
            lab_order_id=lab_order.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            result_number="RES-ORPHAN-DOCTOR",
            reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        )
        await repo.add(lab_result)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
