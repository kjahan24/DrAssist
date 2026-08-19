"""Unit tests for `RejectDoctorVerificationService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.application.dto import RejectDoctorVerificationInput
from app.modules.community_moderation.application.services.reject_doctor_verification_service import (  # noqa: E501
    RejectDoctorVerificationService,
)
from app.modules.community_moderation.domain.entities import DoctorVerification
from app.modules.community_moderation.domain.enums import VerificationStatus
from app.modules.community_moderation.domain.events import DoctorVerificationRejected
from app.modules.community_moderation.domain.exceptions import (
    CannotVerifySelfError,
    DoctorVerificationNotFoundError,
    DoctorVerificationNotPendingError,
)
from tests.unit.modules.community_moderation.application.fakes import (
    FakeDoctorVerificationRepository,
    FakeUnitOfWork,
)


def _seeded() -> (
    tuple[RejectDoctorVerificationService, FakeDoctorVerificationRepository, FakeUnitOfWork]
):
    verifications = FakeDoctorVerificationRepository()
    uow = FakeUnitOfWork()
    service = RejectDoctorVerificationService(
        verification_repository=verifications, unit_of_work=uow
    )
    return service, verifications, uow


class TestRejectDoctorVerification:
    async def test_rejects_a_pending_verification(self) -> None:
        service, verifications, _ = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)

        output = await service.execute(
            RejectDoctorVerificationInput(
                verification_id=verification.id,
                verifier_id=uuid4(),
                reason="Unverifiable license.",
            )
        )
        assert output.status is VerificationStatus.REJECTED
        assert output.rejection_reason == "Unverifiable license."

    async def test_unknown_verification_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(DoctorVerificationNotFoundError):
            await service.execute(
                RejectDoctorVerificationInput(
                    verification_id=uuid4(), verifier_id=uuid4(), reason="N/A"
                )
            )

    async def test_cannot_reject_own_request(self) -> None:
        service, verifications, _ = _seeded()
        user_id = uuid4()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=user_id, organization_id=uuid4()
        )
        await verifications.add(verification)
        with pytest.raises(CannotVerifySelfError):
            await service.execute(
                RejectDoctorVerificationInput(
                    verification_id=verification.id, verifier_id=user_id, reason="N/A"
                )
            )

    async def test_raises_when_already_verified(self) -> None:
        service, verifications, _ = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        verification.approve(verifier_id=uuid4())
        await verifications.add(verification)
        with pytest.raises(DoctorVerificationNotPendingError):
            await service.execute(
                RejectDoctorVerificationInput(
                    verification_id=verification.id, verifier_id=uuid4(), reason="Too late."
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, verifications, uow = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)
        await service.execute(
            RejectDoctorVerificationInput(
                verification_id=verification.id, verifier_id=uuid4(), reason="Rejected."
            )
        )
        assert uow.committed is True

    async def test_publishes_a_rejected_event(self) -> None:
        service, verifications, uow = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)
        await service.execute(
            RejectDoctorVerificationInput(
                verification_id=verification.id, verifier_id=uuid4(), reason="Rejected."
            )
        )
        assert any(isinstance(e, DoctorVerificationRejected) for e in uow.published_events)
