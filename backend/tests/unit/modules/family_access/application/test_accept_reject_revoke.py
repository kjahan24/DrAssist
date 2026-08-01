"""Unit tests for `AcceptInvitation`, `RejectInvitation`, and
`RevokeAccess` — each a thin `UseCase` wrapping one `FamilyAccess`
transition method, using an in-memory fake repository."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.family_access.application.dto import (
    AcceptInvitationInput,
    RejectInvitationInput,
    RevokeAccessInput,
)
from app.modules.family_access.application.use_cases.accept_invitation import AcceptInvitation
from app.modules.family_access.application.use_cases.reject_invitation import RejectInvitation
from app.modules.family_access.application.use_cases.revoke_access import RevokeAccess
from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.enums import AccessLevel, FamilyAccessStatus, Relationship
from app.modules.family_access.domain.exceptions import (
    FamilyAccessNotFoundError,
    InvitationExpiredError,
)
from app.modules.family_access.domain.value_objects import InvitationTokenHash
from tests.unit.modules.family_access.application.fakes import (
    FakeFamilyAccessRepository,
    FakeUnitOfWork,
)

_NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def _make_grant(**overrides: object) -> FamilyAccess:
    """`invitation_expires_at` defaults relative to the real wall clock
    (`datetime.now(UTC)`), not the fixed `_NOW` constant — `AcceptInvitation`
    calls `datetime.now(UTC)` internally (see its own use case), so a
    fixed past timestamp here would make every accept-a-fresh-invitation
    test spuriously look expired."""
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "caregiver_user_id": uuid4(),
        "relationship": Relationship.SPOUSE,
        "access_level": AccessLevel.FULL_MEDICAL,
        "invitation_token": InvitationTokenHash("a" * 64),
        "invitation_expires_at": datetime.now(UTC) + timedelta(days=7),
    }
    defaults.update(overrides)
    return FamilyAccess.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def family_access_repository() -> FakeFamilyAccessRepository:
    return FakeFamilyAccessRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


class TestAcceptInvitation:
    async def test_accepts_a_pending_invitation(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        grant = _make_grant()
        await family_access_repository.add(grant)
        use_case = AcceptInvitation(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )

        output = await use_case.execute(AcceptInvitationInput(family_access_id=grant.id))

        assert output.status is FamilyAccessStatus.ACCEPTED
        stored = await family_access_repository.get_by_id(grant.id)
        assert stored is not None
        assert stored.status is FamilyAccessStatus.ACCEPTED
        assert unit_of_work.committed is True

    async def test_unknown_grant_raises(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = AcceptInvitation(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )
        with pytest.raises(FamilyAccessNotFoundError):
            await use_case.execute(AcceptInvitationInput(family_access_id=uuid4()))

    async def test_expired_invitation_cannot_be_accepted(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        grant = _make_grant(invitation_expires_at=_NOW)
        await family_access_repository.add(grant)
        use_case = AcceptInvitation(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )

        with pytest.raises(InvitationExpiredError):
            await use_case.execute(AcceptInvitationInput(family_access_id=grant.id))


class TestRejectInvitation:
    async def test_rejects_a_pending_invitation(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        grant = _make_grant()
        await family_access_repository.add(grant)
        use_case = RejectInvitation(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )

        output = await use_case.execute(RejectInvitationInput(family_access_id=grant.id))

        assert output.status is FamilyAccessStatus.REJECTED
        assert unit_of_work.committed is True

    async def test_unknown_grant_raises(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = RejectInvitation(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )
        with pytest.raises(FamilyAccessNotFoundError):
            await use_case.execute(RejectInvitationInput(family_access_id=uuid4()))


class TestRevokeAccess:
    async def test_revokes_an_accepted_grant(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        grant = _make_grant()
        grant.accept(now=_NOW)
        await family_access_repository.add(grant)
        use_case = RevokeAccess(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )

        output = await use_case.execute(RevokeAccessInput(family_access_id=grant.id))

        assert output.status is FamilyAccessStatus.REVOKED
        assert unit_of_work.committed is True

    async def test_revokes_a_pending_grant(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        grant = _make_grant()
        await family_access_repository.add(grant)
        use_case = RevokeAccess(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )

        output = await use_case.execute(RevokeAccessInput(family_access_id=grant.id))

        assert output.status is FamilyAccessStatus.REVOKED

    async def test_unknown_grant_raises(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = RevokeAccess(
            family_access_repository=family_access_repository, unit_of_work=unit_of_work
        )
        with pytest.raises(FamilyAccessNotFoundError):
            await use_case.execute(RevokeAccessInput(family_access_id=uuid4()))
