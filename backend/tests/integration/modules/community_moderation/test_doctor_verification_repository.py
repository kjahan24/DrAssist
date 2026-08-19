"""Integration tests for `SqlAlchemyDoctorVerificationRepository` against
a real PostgreSQL instance: round-trip persistence (including the
`verification_metadata` JSONB column), `get_by_doctor_id`, and the
`uq_doctor_verifications_doctor_id` unique constraint."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_moderation._helpers import (
    persist_doctor,
    persist_org_user,
)

from app.modules.community_moderation.domain.entities import DoctorVerification
from app.modules.community_moderation.domain.enums import VerificationStatus
from app.modules.community_moderation.infrastructure.repositories import (
    SqlAlchemyDoctorVerificationRepository,
)


class TestDoctorVerificationRoundTrip:
    async def test_save_and_reload(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        doctor = await persist_doctor(db_session, organization_id=organization.id, user_id=user.id)
        repo = SqlAlchemyDoctorVerificationRepository(db_session)
        verification = DoctorVerification.request(
            doctor_id=doctor.id,
            user_id=user.id,
            organization_id=organization.id,
            specialty="Cardiology",
            metadata={"submitted_documents": ["license.pdf"]},
        )

        await repo.add(verification)
        await db_session.commit()

        reloaded = await repo.get_by_id(verification.id)
        assert reloaded is not None
        assert reloaded.doctor_id == doctor.id
        assert reloaded.user_id == user.id
        assert reloaded.organization_id == organization.id
        assert reloaded.status is VerificationStatus.PENDING
        assert reloaded.specialty == "Cardiology"
        assert reloaded.metadata == {"submitted_documents": ["license.pdf"]}

    async def test_round_trip_preserves_approval_fields(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        doctor = await persist_doctor(db_session, organization_id=organization.id, user_id=user.id)
        _, verifier = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorVerificationRepository(db_session)
        verification = DoctorVerification.request(
            doctor_id=doctor.id, user_id=user.id, organization_id=organization.id
        )
        verifier_id = verifier.id
        verification.approve(verifier_id=verifier_id, specialty="Oncology")
        await repo.add(verification)
        await db_session.commit()

        reloaded = await repo.get_by_id(verification.id)
        assert reloaded is not None
        assert reloaded.status is VerificationStatus.VERIFIED
        assert reloaded.verifier_id == verifier_id
        assert reloaded.verified_at is not None
        assert reloaded.specialty == "Oncology"

    async def test_round_trip_preserves_updates_after_resubmit(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_org_user(db_session)
        doctor = await persist_doctor(db_session, organization_id=organization.id, user_id=user.id)
        _, verifier = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorVerificationRepository(db_session)
        verification = DoctorVerification.request(
            doctor_id=doctor.id, user_id=user.id, organization_id=organization.id
        )
        verification.reject(verifier_id=verifier.id, reason="Missing documents.")
        await repo.add(verification)
        await db_session.commit()

        verification.resubmit(specialty="Dermatology")
        await repo.add(verification)
        await db_session.commit()

        reloaded = await repo.get_by_id(verification.id)
        assert reloaded is not None
        assert reloaded.status is VerificationStatus.PENDING
        assert reloaded.specialty == "Dermatology"
        assert reloaded.rejection_reason is None


class TestGetByDoctorId:
    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyDoctorVerificationRepository(db_session)
        result = await repo.get_by_doctor_id(uuid4())
        assert result is None

    async def test_returns_the_matching_verification(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        doctor = await persist_doctor(db_session, organization_id=organization.id, user_id=user.id)
        repo = SqlAlchemyDoctorVerificationRepository(db_session)
        verification = DoctorVerification.request(
            doctor_id=doctor.id, user_id=user.id, organization_id=organization.id
        )
        await repo.add(verification)
        await db_session.commit()

        found = await repo.get_by_doctor_id(doctor.id)
        assert found is not None
        assert found.id == verification.id


class TestUniqueDoctorIdConstraint:
    async def test_duplicate_doctor_id_row_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_org_user(db_session)
        doctor = await persist_doctor(db_session, organization_id=organization.id, user_id=user.id)
        repo = SqlAlchemyDoctorVerificationRepository(db_session)

        first = DoctorVerification.request(
            doctor_id=doctor.id, user_id=user.id, organization_id=organization.id
        )
        await repo.add(first)
        await db_session.commit()

        second = DoctorVerification.request(
            doctor_id=doctor.id, user_id=user.id, organization_id=organization.id
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestDoctorVerificationRequiresValidReferences:
    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorVerificationRepository(db_session)
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=user.id, organization_id=organization.id
        )
        await repo.add(verification)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
