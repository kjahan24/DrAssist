"""Unit tests for `ApproveDoctorVerificationService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.application.dto import ApproveDoctorVerificationInput
from app.modules.community_moderation.application.services.approve_doctor_verification_service import (  # noqa: E501
    ApproveDoctorVerificationService,
)
from app.modules.community_moderation.domain.entities import DoctorVerification
from app.modules.community_moderation.domain.enums import VerificationStatus
from app.modules.community_moderation.domain.events import DoctorVerificationApproved
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
    tuple[ApproveDoctorVerificationService, FakeDoctorVerificationRepository, FakeUnitOfWork]
):
    verifications = FakeDoctorVerificationRepository()
    uow = FakeUnitOfWork()
    service = ApproveDoctorVerificationService(
        verification_repository=verifications, unit_of_work=uow
    )
    return service, verifications, uow


class TestApproveDoctorVerification:
    async def test_approves_a_pending_verification(self) -> None:
        service, verifications, _ = _seeded()
        doctor_id, user_id = uuid4(), uuid4()
        verification = DoctorVerification.request(
            doctor_id=doctor_id, user_id=user_id, organization_id=uuid4()
        )
        await verifications.add(verification)
        verifier_id = uuid4()

        output = await service.execute(
            ApproveDoctorVerificationInput(verification_id=verification.id, verifier_id=verifier_id)
        )
        assert output.status is VerificationStatus.VERIFIED
        assert output.verifier_id == verifier_id

    async def test_can_set_specialty_on_approval(self) -> None:
        service, verifications, _ = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)
        output = await service.execute(
            ApproveDoctorVerificationInput(
                verification_id=verification.id, verifier_id=uuid4(), specialty="Neurology"
            )
        )
        assert output.specialty == "Neurology"

    async def test_unknown_verification_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(DoctorVerificationNotFoundError):
            await service.execute(
                ApproveDoctorVerificationInput(verification_id=uuid4(), verifier_id=uuid4())
            )

    async def test_cannot_approve_own_request(self) -> None:
        service, verifications, _ = _seeded()
        user_id = uuid4()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=user_id, organization_id=uuid4()
        )
        await verifications.add(verification)
        with pytest.raises(CannotVerifySelfError):
            await service.execute(
                ApproveDoctorVerificationInput(verification_id=verification.id, verifier_id=user_id)
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
                ApproveDoctorVerificationInput(verification_id=verification.id, verifier_id=uuid4())
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, verifications, uow = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)
        await service.execute(
            ApproveDoctorVerificationInput(verification_id=verification.id, verifier_id=uuid4())
        )
        assert uow.committed is True

    async def test_publishes_an_approved_event(self) -> None:
        service, verifications, uow = _seeded()
        verification = DoctorVerification.request(
            doctor_id=uuid4(), user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)
        await service.execute(
            ApproveDoctorVerificationInput(verification_id=verification.id, verifier_id=uuid4())
        )
        assert any(isinstance(e, DoctorVerificationApproved) for e in uow.published_events)
