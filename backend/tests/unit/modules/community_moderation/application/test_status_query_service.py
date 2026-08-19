"""Unit tests for `GetModerationStatusService`/`GetVerificationStatusService`."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.community_moderation.application.dto import GetModerationStatusInput
from app.modules.community_moderation.application.services.status_query_service import (
    GetModerationStatusService,
    GetVerificationStatusService,
)
from app.modules.community_moderation.domain.entities import (
    DoctorVerification,
    ModerationRestriction,
)
from app.modules.community_moderation.domain.enums import ModerationRestrictionType
from tests.unit.modules.community_moderation.application.fakes import (
    FakeDoctorVerificationRepository,
    FakeModerationRestrictionRepository,
)


def _make_restriction(**overrides: object) -> ModerationRestriction:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "community_id": uuid4(),
        "user_id": uuid4(),
        "issued_by": uuid4(),
        "restriction_type": ModerationRestrictionType.WARNING,
        "reason": "Reason.",
    }
    defaults.update(overrides)
    return ModerationRestriction.issue(**defaults)  # type: ignore[arg-type]


class TestGetModerationStatus:
    async def test_returns_not_restricted_when_no_restrictions_exist(self) -> None:
        restrictions = FakeModerationRestrictionRepository()
        service = GetModerationStatusService(restriction_repository=restrictions)
        user_id = uuid4()

        status = await service.get_status(GetModerationStatusInput(user_id=user_id))
        assert status.is_restricted is False
        assert status.current_restriction_type is None
        assert status.active_restriction_count == 0

    async def test_returns_the_most_severe_active_restriction(self) -> None:
        restrictions = FakeModerationRestrictionRepository()
        service = GetModerationStatusService(restriction_repository=restrictions)
        user_id, community_id = uuid4(), uuid4()
        await restrictions.add(
            _make_restriction(
                user_id=user_id,
                community_id=community_id,
                restriction_type=ModerationRestrictionType.WARNING,
            )
        )
        await restrictions.add(
            _make_restriction(
                user_id=user_id,
                community_id=community_id,
                restriction_type=ModerationRestrictionType.SUSPENSION,
                ends_at=datetime.now(UTC) + timedelta(days=5),
            )
        )

        status = await service.get_status(
            GetModerationStatusInput(user_id=user_id, community_id=community_id)
        )
        assert status.current_restriction_type is ModerationRestrictionType.SUSPENSION
        assert status.active_restriction_count == 2
        assert status.is_restricted is True

    async def test_ignores_expired_restrictions(self) -> None:
        restrictions = FakeModerationRestrictionRepository()
        service = GetModerationStatusService(restriction_repository=restrictions)
        user_id = uuid4()
        await restrictions.add(
            _make_restriction(
                user_id=user_id,
                restriction_type=ModerationRestrictionType.SUSPENSION,
                starts_at=datetime.now(UTC) - timedelta(days=10),
                ends_at=datetime.now(UTC) - timedelta(days=1),
            )
        )

        status = await service.get_status(GetModerationStatusInput(user_id=user_id))
        assert status.is_restricted is False

    async def test_permanent_ban_outranks_suspension(self) -> None:
        restrictions = FakeModerationRestrictionRepository()
        service = GetModerationStatusService(restriction_repository=restrictions)
        user_id = uuid4()
        await restrictions.add(
            _make_restriction(
                user_id=user_id,
                restriction_type=ModerationRestrictionType.SUSPENSION,
                ends_at=datetime.now(UTC) + timedelta(days=5),
            )
        )
        await restrictions.add(
            _make_restriction(
                user_id=user_id, restriction_type=ModerationRestrictionType.PERMANENT_BAN
            )
        )

        status = await service.get_status(GetModerationStatusInput(user_id=user_id))
        assert status.current_restriction_type is ModerationRestrictionType.PERMANENT_BAN

    async def test_scoped_to_community_when_given(self) -> None:
        restrictions = FakeModerationRestrictionRepository()
        service = GetModerationStatusService(restriction_repository=restrictions)
        user_id, community_a, community_b = uuid4(), uuid4(), uuid4()
        await restrictions.add(_make_restriction(user_id=user_id, community_id=community_a))

        status = await service.get_status(
            GetModerationStatusInput(user_id=user_id, community_id=community_b)
        )
        assert status.is_restricted is False


class TestGetVerificationStatus:
    async def test_returns_the_matching_verification(self) -> None:
        verifications = FakeDoctorVerificationRepository()
        service = GetVerificationStatusService(verification_repository=verifications)
        doctor_id = uuid4()
        verification = DoctorVerification.request(
            doctor_id=doctor_id, user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)

        result = await service.get_status(doctor_id)
        assert result is not None
        assert result.doctor_id == doctor_id

    async def test_returns_none_when_no_verification_exists(self) -> None:
        verifications = FakeDoctorVerificationRepository()
        service = GetVerificationStatusService(verification_repository=verifications)
        result = await service.get_status(uuid4())
        assert result is None
