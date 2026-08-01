"""Unit tests for `FamilyAccessQueryService` — backs the module's public
`FamilyAccessQueryPort` facade."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.security.invitation_token_hashing import (
    generate_raw_invitation_token,
    hash_invitation_token,
)
from app.modules.family_access.application.services.family_access_query_service import (
    FamilyAccessQueryService,
)
from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.enums import AccessLevel, Relationship
from app.modules.family_access.domain.value_objects import InvitationTokenHash
from tests.unit.modules.family_access.application.fakes import FakeFamilyAccessRepository

_NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def _make_grant(**overrides: object) -> FamilyAccess:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "caregiver_user_id": uuid4(),
        "relationship": Relationship.SPOUSE,
        "access_level": AccessLevel.FULL_MEDICAL,
        "invitation_token": InvitationTokenHash("a" * 64),
        "invitation_expires_at": _NOW + timedelta(days=7),
    }
    defaults.update(overrides)
    return FamilyAccess.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeFamilyAccessRepository:
    return FakeFamilyAccessRepository()


@pytest.fixture
def service(repo: FakeFamilyAccessRepository) -> FamilyAccessQueryService:
    return FamilyAccessQueryService(family_access_repository=repo)


class TestFamilyAccessExists:
    async def test_true_for_a_known_grant(
        self, service: FamilyAccessQueryService, repo: FakeFamilyAccessRepository
    ) -> None:
        grant = _make_grant()
        await repo.add(grant)
        assert await service.family_access_exists(grant.id) is True

    async def test_false_for_an_unknown_grant(self, service: FamilyAccessQueryService) -> None:
        assert await service.family_access_exists(uuid4()) is False


class TestGetPatientCaregivers:
    async def test_returns_grants_ordered_newest_first_scoped_to_the_patient(
        self, service: FamilyAccessQueryService, repo: FakeFamilyAccessRepository
    ) -> None:
        patient_id = uuid4()
        earlier = _make_grant(patient_id=patient_id)
        earlier.created_at = _NOW
        later = _make_grant(patient_id=patient_id)
        later.created_at = _NOW + timedelta(hours=1)
        unrelated = _make_grant(patient_id=uuid4())
        await repo.add(earlier)
        await repo.add(later)
        await repo.add(unrelated)

        summaries = await service.get_patient_caregivers(patient_id)

        assert [s.family_access_id for s in summaries] == [later.id, earlier.id]

    async def test_returns_empty_list_for_a_patient_without_caregivers(
        self, service: FamilyAccessQueryService
    ) -> None:
        assert await service.get_patient_caregivers(uuid4()) == []


class TestGetCaregiverPatients:
    async def test_returns_grants_scoped_to_the_caregiver(
        self, service: FamilyAccessQueryService, repo: FakeFamilyAccessRepository
    ) -> None:
        caregiver_user_id = uuid4()
        matching = _make_grant(caregiver_user_id=caregiver_user_id)
        unrelated = _make_grant(caregiver_user_id=uuid4())
        await repo.add(matching)
        await repo.add(unrelated)

        summaries = await service.get_caregiver_patients(caregiver_user_id)

        assert [s.family_access_id for s in summaries] == [matching.id]


class TestGetInvitationByToken:
    async def test_resolves_by_the_raw_token(
        self, service: FamilyAccessQueryService, repo: FakeFamilyAccessRepository
    ) -> None:
        raw_token = generate_raw_invitation_token()
        grant = _make_grant(invitation_token=InvitationTokenHash(hash_invitation_token(raw_token)))
        await repo.add(grant)

        summary = await service.get_invitation_by_token(raw_token)

        assert summary is not None
        assert summary.family_access_id == grant.id

    async def test_returns_none_for_an_unknown_token(
        self, service: FamilyAccessQueryService
    ) -> None:
        assert await service.get_invitation_by_token(generate_raw_invitation_token()) is None


class TestListPendingInvitations:
    async def test_returns_only_pending_grants_for_the_caregiver(
        self, service: FamilyAccessQueryService, repo: FakeFamilyAccessRepository
    ) -> None:
        caregiver_user_id = uuid4()
        pending = _make_grant(caregiver_user_id=caregiver_user_id)
        accepted = _make_grant(caregiver_user_id=caregiver_user_id)
        accepted.accept(now=_NOW)
        await repo.add(pending)
        await repo.add(accepted)

        summaries = await service.list_pending_invitations(caregiver_user_id)

        assert [s.family_access_id for s in summaries] == [pending.id]


class TestGetActiveAccessLevel:
    async def test_returns_the_access_level_for_an_active_grant(
        self, service: FamilyAccessQueryService, repo: FakeFamilyAccessRepository
    ) -> None:
        patient_id = uuid4()
        caregiver_user_id = uuid4()
        grant = _make_grant(
            patient_id=patient_id,
            caregiver_user_id=caregiver_user_id,
            access_level=AccessLevel.LIMITED_MEDICAL,
        )
        await repo.add(grant)

        level = await service.get_active_access_level(
            patient_id=patient_id, caregiver_user_id=caregiver_user_id
        )

        assert level is AccessLevel.LIMITED_MEDICAL

    async def test_returns_none_when_no_active_grant_exists(
        self, service: FamilyAccessQueryService
    ) -> None:
        level = await service.get_active_access_level(patient_id=uuid4(), caregiver_user_id=uuid4())
        assert level is None

    async def test_returns_none_for_a_revoked_grant(
        self, service: FamilyAccessQueryService, repo: FakeFamilyAccessRepository
    ) -> None:
        patient_id = uuid4()
        caregiver_user_id = uuid4()
        grant = _make_grant(patient_id=patient_id, caregiver_user_id=caregiver_user_id)
        grant.revoke(now=_NOW)
        await repo.add(grant)

        level = await service.get_active_access_level(
            patient_id=patient_id, caregiver_user_id=caregiver_user_id
        )

        assert level is None
