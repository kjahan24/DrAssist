"""Unit tests for `ModerationFacade` — exercised through
`ModerationQueryPort` exactly as a future consumer module would call it,
per `docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.community_moderation.domain.entities import (
    DoctorVerification,
    ModerationAction,
    ModerationRestriction,
)
from app.modules.community_moderation.domain.enums import (
    ContentModerationStatus,
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
)
from app.modules.community_moderation.public.facade import ModerationFacade
from app.modules.community_moderation.public.interfaces import ModerationQueryPort
from tests.unit.modules.community_moderation.application.fakes import (
    FakeDoctorVerificationRepository,
    FakeModerationActionRepository,
    FakeModerationRestrictionRepository,
)


def _facade() -> (
    tuple[
        ModerationFacade,
        FakeModerationActionRepository,
        FakeModerationRestrictionRepository,
        FakeDoctorVerificationRepository,
    ]
):
    actions = FakeModerationActionRepository()
    restrictions = FakeModerationRestrictionRepository()
    verifications = FakeDoctorVerificationRepository()
    facade = ModerationFacade(
        action_repository=actions,
        restriction_repository=restrictions,
        verification_repository=verifications,
    )
    return facade, actions, restrictions, verifications


class TestModerationFacade:
    def test_is_a_moderation_query_port(self) -> None:
        facade, _, _, _ = _facade()
        assert isinstance(facade, ModerationQueryPort)

    async def test_content_status_defaults_to_active(self) -> None:
        facade, _, _, _ = _facade()
        status = await facade.get_content_moderation_status(ModerationTargetType.POST, uuid4())
        assert status == ContentModerationStatus.ACTIVE.value

    async def test_content_status_reflects_latest_action(self) -> None:
        facade, actions, _, _ = _facade()
        target_id = uuid4()
        action = ModerationAction.record(
            organization_id=uuid4(),
            actor_id=uuid4(),
            action_type=ModerationActionType.REMOVE,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason="Policy violation.",
            previous_state=ContentModerationStatus.ACTIVE.value,
            new_state=ContentModerationStatus.REMOVED.value,
        )
        await actions.add(action)

        status = await facade.get_content_moderation_status(ModerationTargetType.POST, target_id)
        assert status == ContentModerationStatus.REMOVED.value

    async def test_user_moderation_status_defaults_to_not_restricted(self) -> None:
        facade, _, _, _ = _facade()
        status = await facade.get_user_moderation_status(uuid4())
        assert status.is_restricted is False

    async def test_user_moderation_status_reflects_the_most_severe_active_restriction(
        self,
    ) -> None:
        facade, _, restrictions, _ = _facade()
        user_id = uuid4()
        await restrictions.add(
            ModerationRestriction.issue(
                organization_id=uuid4(),
                community_id=uuid4(),
                user_id=user_id,
                issued_by=uuid4(),
                restriction_type=ModerationRestrictionType.WARNING,
                reason="Reason.",
            )
        )
        await restrictions.add(
            ModerationRestriction.issue(
                organization_id=uuid4(),
                community_id=uuid4(),
                user_id=user_id,
                issued_by=uuid4(),
                restriction_type=ModerationRestrictionType.SUSPENSION,
                reason="Reason.",
                ends_at=datetime.now(UTC) + timedelta(days=3),
            )
        )

        status = await facade.get_user_moderation_status(user_id)
        assert status.current_restriction_type is ModerationRestrictionType.SUSPENSION
        assert status.active_restriction_count == 2

    async def test_get_verification_status_returns_none_when_absent(self) -> None:
        facade, _, _, _ = _facade()
        result = await facade.get_verification_status(uuid4())
        assert result is None

    async def test_get_verification_status_returns_the_matching_summary(self) -> None:
        facade, _, _, verifications = _facade()
        doctor_id = uuid4()
        verification = DoctorVerification.request(
            doctor_id=doctor_id, user_id=uuid4(), organization_id=uuid4()
        )
        await verifications.add(verification)

        result = await facade.get_verification_status(doctor_id)
        assert result is not None
        assert result.doctor_id == doctor_id
