"""Unit tests for the `FamilyAccess` aggregate's invariants, including
the branching `Pending -> {Accepted, Rejected, Revoked, Expired}` /
`Accepted -> Revoked` status graph."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.enums import AccessLevel, FamilyAccessStatus, Relationship
from app.modules.family_access.domain.events import (
    FamilyAccessInvited,
    FamilyAccessStatusChanged,
)
from app.modules.family_access.domain.exceptions import (
    InvalidFamilyAccessStatusTransitionError,
    InvitationExpiredError,
)
from app.modules.family_access.domain.value_objects import InvitationTokenHash

_VALID_TOKEN_HASH = InvitationTokenHash("a" * 64)
_NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def _make_grant(**overrides: object) -> FamilyAccess:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "caregiver_user_id": uuid4(),
        "relationship": Relationship.SPOUSE,
        "access_level": AccessLevel.FULL_MEDICAL,
        "invitation_token": _VALID_TOKEN_HASH,
        "invitation_expires_at": _NOW + timedelta(days=7),
    }
    defaults.update(overrides)
    return FamilyAccess.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_starts_pending_and_records_invited_event(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        caregiver_user_id = uuid4()
        grant = _make_grant(
            organization_id=organization_id,
            patient_id=patient_id,
            caregiver_user_id=caregiver_user_id,
        )

        assert grant.status is FamilyAccessStatus.PENDING
        assert grant.organization_id == organization_id
        assert grant.patient_id == patient_id
        assert grant.caregiver_user_id == caregiver_user_id
        events = grant.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], FamilyAccessInvited)

    def test_default_accepted_and_revoked_at_are_none(self) -> None:
        grant = _make_grant()
        assert grant.accepted_at is None
        assert grant.revoked_at is None

    def test_default_notes_is_none(self) -> None:
        grant = _make_grant()
        assert grant.notes is None

    def test_token_is_stored(self) -> None:
        grant = _make_grant()
        assert grant.invitation_token == _VALID_TOKEN_HASH


class TestAccept:
    def test_accept_moves_pending_to_accepted_and_stamps_accepted_at(self) -> None:
        grant = _make_grant()
        grant.pull_events()

        grant.accept(now=_NOW)

        assert grant.status is FamilyAccessStatus.ACCEPTED
        assert grant.accepted_at == _NOW
        events = grant.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], FamilyAccessStatusChanged)

    def test_accept_after_expiry_raises_and_leaves_status_pending(self) -> None:
        grant = _make_grant(invitation_expires_at=_NOW)

        with pytest.raises(InvitationExpiredError):
            grant.accept(now=_NOW + timedelta(seconds=1))

        assert grant.status is FamilyAccessStatus.PENDING
        assert grant.accepted_at is None

    def test_accept_exactly_at_expiry_is_treated_as_expired(self) -> None:
        grant = _make_grant(invitation_expires_at=_NOW)

        with pytest.raises(InvitationExpiredError):
            grant.accept(now=_NOW)

    def test_accept_twice_raises_invalid_transition(self) -> None:
        grant = _make_grant()
        grant.accept(now=_NOW)

        with pytest.raises(InvalidFamilyAccessStatusTransitionError):
            grant.accept(now=_NOW)

    def test_accept_after_reject_raises_invalid_transition(self) -> None:
        grant = _make_grant()
        grant.reject()

        with pytest.raises(InvalidFamilyAccessStatusTransitionError):
            grant.accept(now=_NOW)


class TestReject:
    def test_reject_moves_pending_to_rejected(self) -> None:
        grant = _make_grant()
        grant.reject()
        assert grant.status is FamilyAccessStatus.REJECTED

    def test_reject_ignores_expiry(self) -> None:
        """Unlike `accept()`, rejecting an already-expired invitation is
        allowed — see `FamilyAccess.reject()`'s own docstring."""
        grant = _make_grant(invitation_expires_at=_NOW)
        grant.reject()
        assert grant.status is FamilyAccessStatus.REJECTED

    def test_reject_after_accept_raises_invalid_transition(self) -> None:
        grant = _make_grant()
        grant.accept(now=_NOW)

        with pytest.raises(InvalidFamilyAccessStatusTransitionError):
            grant.reject()


class TestRevoke:
    def test_revoke_from_pending(self) -> None:
        grant = _make_grant()
        grant.revoke(now=_NOW)
        assert grant.status is FamilyAccessStatus.REVOKED
        assert grant.revoked_at == _NOW

    def test_revoke_from_accepted(self) -> None:
        grant = _make_grant()
        grant.accept(now=_NOW)
        grant.revoke(now=_NOW + timedelta(days=1))
        assert grant.status is FamilyAccessStatus.REVOKED
        assert grant.revoked_at == _NOW + timedelta(days=1)

    def test_revoked_access_cannot_be_restored(self) -> None:
        grant = _make_grant()
        grant.revoke(now=_NOW)

        with pytest.raises(InvalidFamilyAccessStatusTransitionError):
            grant.accept(now=_NOW)
        with pytest.raises(InvalidFamilyAccessStatusTransitionError):
            grant.revoke(now=_NOW)

    def test_revoke_after_reject_raises_invalid_transition(self) -> None:
        grant = _make_grant()
        grant.reject()

        with pytest.raises(InvalidFamilyAccessStatusTransitionError):
            grant.revoke(now=_NOW)


class TestExpire:
    def test_expire_moves_pending_to_expired(self) -> None:
        grant = _make_grant()
        grant.expire()
        assert grant.status is FamilyAccessStatus.EXPIRED

    def test_expire_after_accept_raises_invalid_transition(self) -> None:
        grant = _make_grant()
        grant.accept(now=_NOW)

        with pytest.raises(InvalidFamilyAccessStatusTransitionError):
            grant.expire()
