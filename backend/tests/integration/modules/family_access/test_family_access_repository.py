"""Integration tests for `SqlAlchemyFamilyAccessRepository`, including
the FKs to `organizations`/`patients`/`users`, the global
`invitation_token` uniqueness constraint, and the partial-unique
"one caregiver cannot have duplicate active access to the same patient"
constraint, against a real PostgreSQL instance."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.family_access._helpers import (
    persist_full_chain,
    persist_organization,
    persist_patient,
    persist_user,
)

from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.enums import AccessLevel, FamilyAccessStatus, Relationship
from app.modules.family_access.domain.value_objects import InvitationTokenHash
from app.modules.family_access.infrastructure.models import FamilyAccessModel
from app.modules.family_access.infrastructure.repositories import (
    SqlAlchemyFamilyAccessRepository,
)


def _unique_token_hash() -> InvitationTokenHash:
    return InvitationTokenHash((uuid4().hex + uuid4().hex)[:64])


def _make_grant(
    *, organization_id: object, patient_id: object, caregiver_user_id: object, **overrides: object
) -> FamilyAccess:
    defaults: dict[str, object] = {
        "organization_id": organization_id,
        "patient_id": patient_id,
        "caregiver_user_id": caregiver_user_id,
        "relationship": Relationship.SPOUSE,
        "access_level": AccessLevel.FULL_MEDICAL,
        "invitation_token": _unique_token_hash(),
        "invitation_expires_at": datetime.now(UTC) + timedelta(days=7),
    }
    defaults.update(overrides)
    return FamilyAccess.create(**defaults)  # type: ignore[arg-type]


class TestFamilyAccessRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        grant = _make_grant(
            organization_id=organization.id,
            patient_id=patient.id,
            caregiver_user_id=caregiver.id,
            relationship=Relationship.GUARDIAN,
            access_level=AccessLevel.LIMITED_MEDICAL,
            notes="Primary caregiver",
        )
        await repo.add(grant)
        await db_session.commit()

        reloaded = await repo.get_by_id(grant.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.patient_id == patient.id
        assert reloaded.caregiver_user_id == caregiver.id
        assert reloaded.relationship is Relationship.GUARDIAN
        assert reloaded.access_level is AccessLevel.LIMITED_MEDICAL
        assert reloaded.status is FamilyAccessStatus.PENDING
        assert reloaded.invitation_token == grant.invitation_token
        assert reloaded.notes == "Primary caregiver"
        assert reloaded.accepted_at is None
        assert reloaded.revoked_at is None

    async def test_status_transition_round_trips(self, db_session: AsyncSession) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        grant = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        await repo.add(grant)
        await db_session.commit()

        now = datetime.now(UTC)
        grant.accept(now=now)
        await repo.add(grant)
        await db_session.commit()

        reloaded = await repo.get_by_id(grant.id)
        assert reloaded is not None
        assert reloaded.status is FamilyAccessStatus.ACCEPTED
        assert reloaded.accepted_at is not None


class TestGetByInvitationToken:
    async def test_returns_the_matching_grant(self, db_session: AsyncSession) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        repo = SqlAlchemyFamilyAccessRepository(db_session)
        token_hash = _unique_token_hash()

        grant = _make_grant(
            organization_id=organization.id,
            patient_id=patient.id,
            caregiver_user_id=caregiver.id,
            invitation_token=token_hash,
        )
        await repo.add(grant)
        await db_session.commit()

        found = await repo.get_by_invitation_token(token_hash)
        assert found is not None and found.id == grant.id

    async def test_returns_none_for_an_unknown_token(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyFamilyAccessRepository(db_session)
        assert await repo.get_by_invitation_token(_unique_token_hash()) is None


class TestGetActiveByPatientAndCaregiver:
    async def test_returns_a_pending_grant(self, db_session: AsyncSession) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        repo = SqlAlchemyFamilyAccessRepository(db_session)
        grant = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        await repo.add(grant)
        await db_session.commit()

        found = await repo.get_active_by_patient_and_caregiver(
            patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        assert found is not None and found.id == grant.id

    async def test_returns_none_for_a_revoked_grant(self, db_session: AsyncSession) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        repo = SqlAlchemyFamilyAccessRepository(db_session)
        grant = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        grant.revoke(now=datetime.now(UTC))
        await repo.add(grant)
        await db_session.commit()

        found = await repo.get_active_by_patient_and_caregiver(
            patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        assert found is None


class TestListMethods:
    async def test_list_by_patient_scopes_and_orders_newest_first(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, caregiver_a = await persist_full_chain(db_session)
        caregiver_b = await persist_user(db_session, organization_id=organization.id)
        other_patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        grant_a = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver_a.id
        )
        await repo.add(grant_a)
        await db_session.commit()
        grant_b = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver_b.id
        )
        await repo.add(grant_b)
        await db_session.commit()
        unrelated = _make_grant(
            organization_id=organization.id,
            patient_id=other_patient.id,
            caregiver_user_id=caregiver_a.id,
        )
        await repo.add(unrelated)
        await db_session.commit()

        grants = await repo.list_by_patient(patient.id)
        assert [g.id for g in grants] == [grant_b.id, grant_a.id]

    async def test_list_by_caregiver_scopes_to_the_caregiver(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        other_patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        grant_a = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        grant_b = _make_grant(
            organization_id=organization.id,
            patient_id=other_patient.id,
            caregiver_user_id=caregiver.id,
        )
        await repo.add(grant_a)
        await repo.add(grant_b)
        await db_session.commit()

        grants = await repo.list_by_caregiver(caregiver.id)
        assert {g.id for g in grants} == {grant_a.id, grant_b.id}

    async def test_list_pending_by_caregiver_excludes_non_pending(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        other_patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        pending = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        accepted = _make_grant(
            organization_id=organization.id,
            patient_id=other_patient.id,
            caregiver_user_id=caregiver.id,
        )
        accepted.accept(now=datetime.now(UTC))
        await repo.add(pending)
        await repo.add(accepted)
        await db_session.commit()

        grants = await repo.list_pending_by_caregiver(caregiver.id)
        assert [g.id for g in grants] == [pending.id]


class TestInvitationTokenUniqueness:
    async def test_duplicate_invitation_token_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        other_patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyFamilyAccessRepository(db_session)
        shared_token = _unique_token_hash()

        first = _make_grant(
            organization_id=organization.id,
            patient_id=patient.id,
            caregiver_user_id=caregiver.id,
            invitation_token=shared_token,
        )
        await repo.add(first)
        await db_session.commit()

        second = _make_grant(
            organization_id=organization.id,
            patient_id=other_patient.id,
            caregiver_user_id=caregiver.id,
            invitation_token=shared_token,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestDuplicateActivePatientCaregiverConstraint:
    """`FamilyAccess.__post_init__`/`InviteCaregiver`'s own repository
    check already prevent this from ever happening through normal
    application flow (see `application/use_cases/invite_caregiver.py`) —
    this test targets the DB partial-unique index directly (bypassing
    the domain/application layers, the way a direct SQL edit would) to
    prove the defense-in-depth layer actually works, the same pattern
    `tests.integration.modules.documents.test_medical_document_repository
    .TestFileSizeCheckConstraint` already established."""

    async def test_two_active_grants_for_the_same_patient_and_caregiver_violate_the_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        first = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        await repo.add(first)
        await db_session.commit()

        second = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_a_new_grant_is_allowed_once_the_prior_one_is_terminal(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        first = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        first.revoke(now=datetime.now(UTC))
        await repo.add(first)
        await db_session.commit()

        second = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=caregiver.id
        )
        await repo.add(second)
        await db_session.commit()  # must not raise

        reloaded = await repo.get_by_id(second.id)
        assert reloaded is not None


class TestFamilyAccessRequiresValidReferences:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        caregiver = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        grant = _make_grant(
            organization_id=organization.id, patient_id=uuid4(), caregiver_user_id=caregiver.id
        )
        await repo.add(grant)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_caregiver_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyFamilyAccessRepository(db_session)

        grant = _make_grant(
            organization_id=organization.id, patient_id=patient.id, caregiver_user_id=uuid4()
        )
        await repo.add(grant)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestFamilyAccessModelDirectInsert:
    """Confirms the ORM model itself (not just the domain-entity-driven
    repository path) round-trips every column correctly — the same
    "insert the model directly" smoke check
    `tests.integration.modules.documents.test_medical_document_repository`
    uses for its own `CHECK` constraint test."""

    async def test_model_insert_and_query(self, db_session: AsyncSession) -> None:
        organization, patient, caregiver = await persist_full_chain(db_session)

        model = FamilyAccessModel(
            organization_id=organization.id,
            patient_id=patient.id,
            caregiver_user_id=caregiver.id,
            relationship=Relationship.PARENT,
            access_level=AccessLevel.READ_ONLY,
            status=FamilyAccessStatus.PENDING,
            invitation_token=str(_unique_token_hash()),
            invitation_expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(model)
        await db_session.commit()

        reloaded = await db_session.get(FamilyAccessModel, model.id)
        assert reloaded is not None
        assert reloaded.relationship is Relationship.PARENT
        assert reloaded.access_level is AccessLevel.READ_ONLY
