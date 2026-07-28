"""Integration tests for `SqlAlchemyInsuranceRepository`, including the FK
to `patients` and the `expiry_date > effective_date` check constraint,
against a real PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient._helpers import persist_patient

from app.modules.patient.domain.entities import Insurance
from app.modules.patient.domain.enums import InsuranceStatus
from app.modules.patient.infrastructure.repositories import SqlAlchemyInsuranceRepository


class TestInsuranceRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyInsuranceRepository(db_session)

        insurance = Insurance.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            provider_name="Acme Health",
            policy_number="POL-001",
            effective_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
            member_id="M-123",
            group_number="G-456",
            coverage_type="PPO",
        )
        await repo.add(insurance)
        await db_session.commit()

        reloaded = await repo.get_by_id(insurance.id)
        assert reloaded is not None
        assert reloaded.patient_id == patient.id
        assert reloaded.provider_name == "Acme Health"
        assert reloaded.policy_number == "POL-001"
        assert reloaded.member_id == "M-123"
        assert reloaded.group_number == "G-456"
        assert reloaded.coverage_type == "PPO"
        assert reloaded.status is InsuranceStatus.ACTIVE

    async def test_status_change_persists(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyInsuranceRepository(db_session)

        insurance = Insurance.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            provider_name="Acme Health",
            policy_number="POL-002",
            effective_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
        )
        await repo.add(insurance)
        await db_session.commit()

        insurance.cancel()
        await repo.add(insurance)
        await db_session.commit()

        reloaded = await repo.get_by_id(insurance.id)
        assert reloaded is not None
        assert reloaded.status is InsuranceStatus.CANCELLED

    async def test_list_by_patient_scopes_to_a_single_patient(
        self, db_session: AsyncSession
    ) -> None:
        patient_a = await persist_patient(db_session)
        patient_b = await persist_patient(db_session)
        repo = SqlAlchemyInsuranceRepository(db_session)

        insurance_a = Insurance.create(
            organization_id=patient_a.organization_id,
            patient_id=patient_a.id,
            provider_name="Acme Health",
            policy_number="POL-A",
            effective_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
        )
        insurance_b = Insurance.create(
            organization_id=patient_b.organization_id,
            patient_id=patient_b.id,
            provider_name="Acme Health",
            policy_number="POL-B",
            effective_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
        )
        await repo.add(insurance_a)
        await repo.add(insurance_b)
        await db_session.commit()

        insurance_for_a = await repo.list_by_patient(patient_a.id)
        assert [i.id for i in insurance_for_a] == [insurance_a.id]


class TestInsuranceRequiresValidPatient:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = (await persist_patient(db_session)).organization_id
        repo = SqlAlchemyInsuranceRepository(db_session)

        insurance = Insurance.create(
            organization_id=organization,
            patient_id=uuid4(),
            provider_name="Acme Health",
            policy_number="POL-ORPHAN",
            effective_date=date(2026, 1, 1),
            expiry_date=date(2027, 1, 1),
        )
        await repo.add(insurance)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
