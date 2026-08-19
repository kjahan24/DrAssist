"""Unit tests for `RevokeDoctorVerificationService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.application.dto import RevokeDoctorVerificationInput
from app.modules.community_moderation.application.services.revoke_doctor_verification_service import (  # noqa: E501
    RevokeDoctorVerificationService,
)
from app.modules.community_moderation.domain.entities import DoctorVerification
from app.modules.community_moderation.domain.enums import VerificationStatus
from app.modules.community_moderation.domain.events import DoctorVerificationRevoked
from app.modules.community_moderation.domain.exceptions import (
    CannotVerifySelfError,
    DoctorVerificationNotFoundError,
    DoctorVerificationNotVerifiedError,
)
from tests.unit.modules.community_moderation.application.fakes import (
    FakeDoctorVerificationRepository,
    FakeUnitOfWork,
)


def _seeded() -> (
    tuple[RevokeDoctorVerificationService, FakeDoctorVerificationRepository, FakeUnitOfWork]
):
    verifications = FakeDoctorVerificationRepository()
    uow = FakeUnitOfWork()
    service = RevokeDoctorVerificationService(
        verification_repository=verifications, unit_of_work=uow
    )
    return service, verifications, uow


class TestRevokeDoctorVerification:
    async def test_revokes_a_verified_verification(self) -> None:
        service, verifications, _ = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        verification.approve(verifier_id=uuid4())
        await verifications.add(verification)

        output = await service.execute(
            RevokeDoctorVerificationInput(
                verification_id=verification.id, verifier_id=uuid4(), reason="License lapsed."
            )
        )
        assert output.status is VerificationStatus.REVOKED
        assert output.revocation_reason == "License lapsed."

    async def test_unknown_verification_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(DoctorVerificationNotFoundError):
            await service.execute(
                RevokeDoctorVerificationInput(
                    verification_id=uuid4(), verifier_id=uuid4(), reason="N/A"
                )
            )

    async def test_cannot_revoke_own_verification(self) -> None:
        service, verifications, _ = _seeded()
        user_id = uuid4()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=user_id, organization_id=uuid4()
        )
        verification.approve(verifier_id=uuid4())
        await verifications.add(verification)
        with pytest.raises(CannotVerifySelfError):
            await service.execute(
                RevokeDoctorVerificationInput(
                    verification_id=verification.id, verifier_id=user_id, reason="N/A"
                )
            )

    async def test_raises_when_still_pending(self) -> None:
        service, verifications, _ = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)
        with pytest.raises(DoctorVerificationNotVerifiedError):
            await service.execute(
                RevokeDoctorVerificationInput(
                    verification_id=verification.id, verifier_id=uuid4(), reason="Too early."
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, verifications, uow = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        verification.approve(verifier_id=uuid4())
        await verifications.add(verification)
        await service.execute(
            RevokeDoctorVerificationInput(
                verification_id=verification.id, verifier_id=uuid4(), reason="Revoked."
            )
        )
        assert uow.committed is True

    async def test_publishes_a_revoked_event(self) -> None:
        service, verifications, uow = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        verification.approve(verifier_id=uuid4())
        await verifications.add(verification)
        await service.execute(
            RevokeDoctorVerificationInput(
                verification_id=verification.id, verifier_id=uuid4(), reason="Revoked."
            )
        )
        assert any(isinstance(e, DoctorVerificationRevoked) for e in uow.published_events)
