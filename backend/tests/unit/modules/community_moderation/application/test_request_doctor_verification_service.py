"""Unit tests for `RequestDoctorVerificationService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.application.dto import RequestDoctorVerificationInput
from app.modules.community_moderation.application.services.request_doctor_verification_service import (  # noqa: E501
    RequestDoctorVerificationService,
)
from app.modules.community_moderation.domain.entities import DoctorVerification
from app.modules.community_moderation.domain.enums import VerificationStatus
from app.modules.community_moderation.domain.exceptions import (
    DoctorNotFoundForVerificationError,
    DoctorVerificationAlreadyPendingError,
    DoctorVerificationAlreadyVerifiedError,
)
from tests.unit.modules.community_moderation.application.fakes import (
    FakeDoctorQueryPort,
    FakeDoctorVerificationRepository,
    FakeUnitOfWork,
    make_doctor_summary,
)


def _seeded() -> (
    tuple[
        RequestDoctorVerificationService,
        FakeDoctorVerificationRepository,
        FakeDoctorQueryPort,
        FakeUnitOfWork,
    ]
):
    verifications = FakeDoctorVerificationRepository()
    doctors = FakeDoctorQueryPort()
    uow = FakeUnitOfWork()
    service = RequestDoctorVerificationService(
        verification_repository=verifications, doctor_query_port=doctors, unit_of_work=uow
    )
    return service, verifications, doctors, uow


class TestRequestDoctorVerification:
    async def test_creates_a_pending_verification(self) -> None:
        service, verifications, doctors, _ = _seeded()
        doctor_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        doctors.add_doctor(
            make_doctor_summary(doctor_id=doctor_id, user_id=user_id, organization_id=org_id)
        )

        output = await service.execute(
            RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=user_id)
        )
        assert output.status is VerificationStatus.PENDING
        stored = await verifications.get_by_doctor_id(doctor_id)
        assert stored is not None

    async def test_accepts_specialty_and_metadata(self) -> None:
        service, _, doctors, _ = _seeded()
        doctor_id, user_id = uuid4(), uuid4()
        doctors.add_doctor(make_doctor_summary(doctor_id=doctor_id, user_id=user_id))

        output = await service.execute(
            RequestDoctorVerificationInput(
                doctor_id=doctor_id,
                requesting_user_id=user_id,
                specialty="Cardiology",
                metadata={"license": "12345"},
            )
        )
        assert output.specialty == "Cardiology"
        assert output.metadata == {"license": "12345"}

    async def test_unknown_doctor_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(DoctorNotFoundForVerificationError):
            await service.execute(
                RequestDoctorVerificationInput(doctor_id=uuid4(), requesting_user_id=uuid4())
            )

    async def test_another_users_doctor_id_raises(self) -> None:
        service, _, doctors, _ = _seeded()
        doctor_id, real_user_id = uuid4(), uuid4()
        doctors.add_doctor(make_doctor_summary(doctor_id=doctor_id, user_id=real_user_id))
        with pytest.raises(DoctorNotFoundForVerificationError):
            await service.execute(
                RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=uuid4())
            )

    async def test_already_pending_raises(self) -> None:
        service, _, doctors, _ = _seeded()
        doctor_id, user_id = uuid4(), uuid4()
        doctors.add_doctor(make_doctor_summary(doctor_id=doctor_id, user_id=user_id))
        await service.execute(
            RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=user_id)
        )
        with pytest.raises(DoctorVerificationAlreadyPendingError):
            await service.execute(
                RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=user_id)
            )

    async def test_already_verified_raises(self) -> None:
        service, verifications, doctors, _ = _seeded()
        doctor_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        doctors.add_doctor(
            make_doctor_summary(doctor_id=doctor_id, user_id=user_id, organization_id=org_id)
        )
        existing = DoctorVerification.request(
            doctor_id=doctor_id, user_id=user_id, organization_id=org_id
        )
        existing.approve(verifier_id=uuid4())
        await verifications.add(existing)

        with pytest.raises(DoctorVerificationAlreadyVerifiedError):
            await service.execute(
                RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=user_id)
            )

    async def test_resubmits_after_rejection(self) -> None:
        service, verifications, doctors, _ = _seeded()
        doctor_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        doctors.add_doctor(
            make_doctor_summary(doctor_id=doctor_id, user_id=user_id, organization_id=org_id)
        )
        existing = DoctorVerification.request(
            doctor_id=doctor_id, user_id=user_id, organization_id=org_id
        )
        existing.reject(verifier_id=uuid4(), reason="Missing documents.")
        await verifications.add(existing)
        original_id = existing.id

        output = await service.execute(
            RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=user_id)
        )
        assert output.verification_id == original_id
        assert output.status is VerificationStatus.PENDING

    async def test_resubmits_after_revocation(self) -> None:
        service, verifications, doctors, _ = _seeded()
        doctor_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        doctors.add_doctor(
            make_doctor_summary(doctor_id=doctor_id, user_id=user_id, organization_id=org_id)
        )
        existing = DoctorVerification.request(
            doctor_id=doctor_id, user_id=user_id, organization_id=org_id
        )
        existing.approve(verifier_id=uuid4())
        existing.revoke(verifier_id=uuid4(), reason="License lapsed.")
        await verifications.add(existing)

        output = await service.execute(
            RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=user_id)
        )
        assert output.status is VerificationStatus.PENDING

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, doctors, uow = _seeded()
        doctor_id, user_id = uuid4(), uuid4()
        doctors.add_doctor(make_doctor_summary(doctor_id=doctor_id, user_id=user_id))
        await service.execute(
            RequestDoctorVerificationInput(doctor_id=doctor_id, requesting_user_id=user_id)
        )
        assert uow.committed is True
