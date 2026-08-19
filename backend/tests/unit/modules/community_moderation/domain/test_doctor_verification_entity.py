"""Unit tests for `DoctorVerification`: request/approve/reject/revoke/
resubmit lifecycle transitions and their guards."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.domain.entities import DoctorVerification
from app.modules.community_moderation.domain.enums import VerificationStatus
from app.modules.community_moderation.domain.events import (
    DoctorVerificationApproved,
    DoctorVerificationRejected,
    DoctorVerificationRequested,
    DoctorVerificationRevoked,
)
from app.modules.community_moderation.domain.exceptions import (
    DoctorVerificationCannotBeResubmittedError,
    DoctorVerificationNotPendingError,
    DoctorVerificationNotVerifiedError,
)


def _make_verification(**overrides: object) -> DoctorVerification:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "user_id": uuid4(),
        "organization_id": uuid4(),
    }
    defaults.update(overrides)
    return DoctorVerification.request(**defaults)  # type: ignore[arg-type]


class TestRequest:
    def test_defaults_to_pending_status(self) -> None:
        verification = _make_verification()
        assert verification.status is VerificationStatus.PENDING

    def test_records_a_verification_requested_event(self) -> None:
        verification = _make_verification()
        events = verification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorVerificationRequested)
        assert events[0].verification_id == verification.id

    def test_defaults_metadata_to_an_empty_dict(self) -> None:
        verification = _make_verification()
        assert verification.metadata == {}

    def test_accepts_specialty_and_metadata(self) -> None:
        verification = _make_verification(
            specialty="Cardiology", metadata={"submitted_documents": ["license.pdf"]}
        )
        assert verification.specialty == "Cardiology"
        assert verification.metadata == {"submitted_documents": ["license.pdf"]}

    def test_metadata_is_copied_not_aliased(self) -> None:
        source = {"a": 1}
        verification = _make_verification(metadata=source)
        source["a"] = 2
        assert verification.metadata == {"a": 1}


class TestApprove:
    def test_moves_to_verified_and_stamps_verifier_and_timestamp(self) -> None:
        verification = _make_verification()
        verifier_id = uuid4()
        verification.approve(verifier_id=verifier_id)
        assert verification.status is VerificationStatus.VERIFIED
        assert verification.verifier_id == verifier_id
        assert verification.verified_at is not None

    def test_can_set_specialty_on_approval(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4(), specialty="Oncology")
        assert verification.specialty == "Oncology"

    def test_records_an_approved_event(self) -> None:
        verification = _make_verification()
        verification.pull_events()
        verification.approve(verifier_id=uuid4())
        events = verification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorVerificationApproved)

    def test_raises_when_already_verified(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4())
        with pytest.raises(DoctorVerificationNotPendingError):
            verification.approve(verifier_id=uuid4())

    def test_raises_when_rejected(self) -> None:
        verification = _make_verification()
        verification.reject(verifier_id=uuid4(), reason="Unverifiable license.")
        with pytest.raises(DoctorVerificationNotPendingError):
            verification.approve(verifier_id=uuid4())


class TestReject:
    def test_moves_to_rejected_and_stores_reason(self) -> None:
        verification = _make_verification()
        verifier_id = uuid4()
        verification.reject(verifier_id=verifier_id, reason="Unverifiable license.")
        assert verification.status is VerificationStatus.REJECTED
        assert verification.verifier_id == verifier_id
        assert verification.rejection_reason == "Unverifiable license."

    def test_records_a_rejected_event(self) -> None:
        verification = _make_verification()
        verification.pull_events()
        verification.reject(verifier_id=uuid4(), reason="Unverifiable license.")
        events = verification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorVerificationRejected)

    def test_raises_when_already_verified(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4())
        with pytest.raises(DoctorVerificationNotPendingError):
            verification.reject(verifier_id=uuid4(), reason="Too late.")

    def test_raises_when_already_rejected(self) -> None:
        verification = _make_verification()
        verification.reject(verifier_id=uuid4(), reason="First rejection.")
        with pytest.raises(DoctorVerificationNotPendingError):
            verification.reject(verifier_id=uuid4(), reason="Second rejection.")


class TestRevoke:
    def test_moves_to_revoked_and_stores_reason(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4())
        verifier_id = uuid4()
        verification.revoke(verifier_id=verifier_id, reason="License lapsed.")
        assert verification.status is VerificationStatus.REVOKED
        assert verification.verifier_id == verifier_id
        assert verification.revocation_reason == "License lapsed."

    def test_records_a_revoked_event(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4())
        verification.pull_events()
        verification.revoke(verifier_id=uuid4(), reason="License lapsed.")
        events = verification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorVerificationRevoked)

    def test_raises_when_still_pending(self) -> None:
        verification = _make_verification()
        with pytest.raises(DoctorVerificationNotVerifiedError):
            verification.revoke(verifier_id=uuid4(), reason="Too early.")

    def test_raises_when_already_revoked(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4())
        verification.revoke(verifier_id=uuid4(), reason="First revocation.")
        with pytest.raises(DoctorVerificationNotVerifiedError):
            verification.revoke(verifier_id=uuid4(), reason="Second revocation.")


class TestResubmit:
    def test_resets_from_rejected_to_pending(self) -> None:
        verification = _make_verification()
        verification.reject(verifier_id=uuid4(), reason="Missing documents.")
        verification.resubmit()
        assert verification.status is VerificationStatus.PENDING
        assert verification.verifier_id is None
        assert verification.rejection_reason is None

    def test_resets_from_revoked_to_pending(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4())
        verification.revoke(verifier_id=uuid4(), reason="License lapsed.")
        verification.resubmit()
        assert verification.status is VerificationStatus.PENDING
        assert verification.verifier_id is None
        assert verification.verified_at is None
        assert verification.revocation_reason is None

    def test_records_a_new_requested_event(self) -> None:
        verification = _make_verification()
        verification.reject(verifier_id=uuid4(), reason="Missing documents.")
        verification.pull_events()
        verification.resubmit()
        events = verification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorVerificationRequested)

    def test_can_update_specialty_and_metadata_on_resubmit(self) -> None:
        verification = _make_verification()
        verification.reject(verifier_id=uuid4(), reason="Missing documents.")
        verification.resubmit(specialty="Neurology", metadata={"license.pdf": "resubmitted"})
        assert verification.specialty == "Neurology"
        assert verification.metadata == {"license.pdf": "resubmitted"}

    def test_raises_when_still_pending(self) -> None:
        verification = _make_verification()
        with pytest.raises(DoctorVerificationCannotBeResubmittedError):
            verification.resubmit()

    def test_raises_when_verified(self) -> None:
        verification = _make_verification()
        verification.approve(verifier_id=uuid4())
        with pytest.raises(DoctorVerificationCannotBeResubmittedError):
            verification.resubmit()
