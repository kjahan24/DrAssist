"""Integration tests for `SqlAlchemyVisitVitalSignsRepository`, including
the FKs to `organizations`/`patient_visits`/`doctors`, the per-visit
one-to-one uniqueness constraint, and the numeric-range `CHECK`
constraints, against a real PostgreSQL instance."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.vital_signs._helpers import (
    persist_doctor,
    persist_organization,
    persist_patient,
    persist_visit,
)

from app.modules.doctor.domain.entities import Doctor
from app.modules.organization.domain.entities import Organization
from app.modules.patient.domain.entities import Patient
from app.modules.visit.domain.entities import PatientVisit
from app.modules.vital_signs.domain.entities import VisitVitalSigns
from app.modules.vital_signs.domain.value_objects import BloodPressure
from app.modules.vital_signs.infrastructure.models import VisitVitalSignsModel
from app.modules.vital_signs.infrastructure.repositories import (
    SqlAlchemyVisitVitalSignsRepository,
)

_DEFAULT_BP = BloodPressure(systolic=120, diastolic=80)


async def _persist_full_chain(
    db_session: AsyncSession,
) -> tuple[Organization, Patient, Doctor, PatientVisit]:
    organization = await persist_organization(db_session)
    patient = await persist_patient(db_session, organization_id=organization.id)
    doctor = await persist_doctor(db_session, organization_id=organization.id)
    visit = await persist_visit(
        db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
    )
    return organization, patient, doctor, visit


class TestVisitVitalSignsRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, _patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitVitalSignsRepository(db_session)

        vital_signs = VisitVitalSigns.create(
            organization_id=organization.id,
            visit_id=visit.id,
            recorded_by=doctor.id,
            height_cm=Decimal("170"),
            weight_kg=Decimal("70"),
            temperature_c=Decimal("37.2"),
            pulse_bpm=72,
            respiratory_rate=16,
            blood_pressure=_DEFAULT_BP,
            spo2=98,
            blood_glucose=Decimal("95.0"),
            pain_score=2,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(vital_signs)
        await db_session.commit()

        reloaded = await repo.get_by_id(vital_signs.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.visit_id == visit.id
        assert reloaded.recorded_by == doctor.id
        assert reloaded.height_cm == Decimal("170.00")
        assert reloaded.weight_kg == Decimal("70.00")
        assert reloaded.bmi == Decimal("24.2")
        assert reloaded.temperature_c == Decimal("37.2")
        assert reloaded.pulse_bpm == 72
        assert reloaded.respiratory_rate == 16
        assert reloaded.blood_pressure == _DEFAULT_BP
        assert reloaded.spo2 == 98
        assert reloaded.blood_glucose == Decimal("95.0")
        assert reloaded.pain_score == 2

    async def test_optional_fields_round_trip_as_none(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitVitalSignsRepository(db_session)

        vital_signs = VisitVitalSigns.create(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            blood_pressure=_DEFAULT_BP,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(vital_signs)
        await db_session.commit()

        reloaded = await repo.get_by_id(vital_signs.id)
        assert reloaded is not None
        assert reloaded.recorded_by is None
        assert reloaded.height_cm is None
        assert reloaded.weight_kg is None
        assert reloaded.bmi is None
        assert reloaded.blood_glucose is None
        assert reloaded.pain_score is None


class TestGetByVisitId:
    async def test_returns_the_record_for_that_visit(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitVitalSignsRepository(db_session)

        vital_signs = VisitVitalSigns.create(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            blood_pressure=_DEFAULT_BP,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(vital_signs)
        await db_session.commit()

        found = await repo.get_by_visit_id(visit.id)
        assert found is not None and found.id == vital_signs.id

    async def test_returns_none_for_a_visit_without_vital_signs(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyVisitVitalSignsRepository(db_session)
        assert await repo.get_by_visit_id(uuid4()) is None


class TestOneToOneUniqueness:
    async def test_a_second_record_for_the_same_visit_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitVitalSignsRepository(db_session)

        first = VisitVitalSigns.create(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            blood_pressure=_DEFAULT_BP,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(first)
        await db_session.commit()

        second = VisitVitalSigns.create(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.5"),
            pulse_bpm=80,
            respiratory_rate=18,
            blood_pressure=_DEFAULT_BP,
            spo2=97,
            recorded_at=datetime(2026, 1, 1, 9, 30),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestVisitVitalSignsRequiresValidReferences:
    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyVisitVitalSignsRepository(db_session)

        vital_signs = VisitVitalSigns.create(
            organization_id=organization.id,
            visit_id=uuid4(),
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            blood_pressure=_DEFAULT_BP,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(vital_signs)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_recorded_by_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitVitalSignsRepository(db_session)

        vital_signs = VisitVitalSigns.create(
            organization_id=organization.id,
            visit_id=visit.id,
            recorded_by=uuid4(),
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            blood_pressure=_DEFAULT_BP,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(vital_signs)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestNumericRangeCheckConstraints:
    """`VisitVitalSigns.__post_init__` already prevents these states from
    ever existing via the domain layer — these tests target the DB
    `CHECK` constraints directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.visit.test_patient_visit_repository.TestCheckOutCheckConstraint`
    already established."""

    async def test_systolic_not_greater_than_diastolic_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitVitalSignsModel(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            systolic_bp=80,
            diastolic_bp=80,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_spo2_above_100_violates_check_constraint(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitVitalSignsModel(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            systolic_bp=120,
            diastolic_bp=80,
            spo2=101,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_temperature_outside_range_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitVitalSignsModel(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("50.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            systolic_bp=120,
            diastolic_bp=80,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_non_positive_pulse_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitVitalSignsModel(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=0,
            respiratory_rate=16,
            systolic_bp=120,
            diastolic_bp=80,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_non_positive_respiratory_rate_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitVitalSignsModel(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=0,
            systolic_bp=120,
            diastolic_bp=80,
            spo2=98,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_pain_score_above_10_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitVitalSignsModel(
            organization_id=organization.id,
            visit_id=visit.id,
            temperature_c=Decimal("37.0"),
            pulse_bpm=72,
            respiratory_rate=16,
            systolic_bp=120,
            diastolic_bp=80,
            spo2=98,
            pain_score=11,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
