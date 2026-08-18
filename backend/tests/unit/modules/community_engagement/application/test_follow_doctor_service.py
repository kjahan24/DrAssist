"""Unit tests for `FollowDoctorService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_engagement.application.dto import FollowDoctorInput
from app.modules.community_engagement.application.services.follow_doctor_service import (
    FollowDoctorService,
)
from app.modules.community_engagement.domain.enums import FollowTargetType
from app.modules.community_engagement.domain.events import DoctorFollowed
from app.modules.community_engagement.domain.exceptions import (
    CannotFollowSelfError,
    UserNotFoundForFollowError,
)
from tests.unit.modules.community_engagement.application.fakes import (
    FakeDoctorFollowerRepository,
    FakeUnitOfWork,
    FakeUserQueryPort,
    make_user_summary,
)


def _seeded() -> (
    tuple[FollowDoctorService, FakeDoctorFollowerRepository, FakeUserQueryPort, FakeUnitOfWork]
):
    followers = FakeDoctorFollowerRepository()
    users = FakeUserQueryPort()
    uow = FakeUnitOfWork()
    service = FollowDoctorService(
        doctor_follower_repository=followers, user_query_port=users, unit_of_work=uow
    )
    return service, followers, users, uow


class TestFollowDoctor:
    async def test_creates_a_follow(self) -> None:
        service, followers, users, _ = _seeded()
        followed_id, follower_id, org_id = uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=followed_id, organization_id=org_id))

        result = await service.execute(
            FollowDoctorInput(
                follower_user_id=follower_id, organization_id=org_id, followed_user_id=followed_id
            )
        )
        assert result.follow_target_type is FollowTargetType.DOCTOR
        assert result.target_id == followed_id
        assert result.user_id == follower_id
        stored = await followers.get_follow(follower_id, followed_id)
        assert stored is not None

    async def test_following_yourself_raises(self) -> None:
        service, _, users, _ = _seeded()
        user_id, org_id = uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=user_id, organization_id=org_id))

        with pytest.raises(CannotFollowSelfError):
            await service.execute(
                FollowDoctorInput(
                    follower_user_id=user_id, organization_id=org_id, followed_user_id=user_id
                )
            )

    async def test_self_follow_check_happens_before_any_lookup(self) -> None:
        """No user needs to be seeded — the self-follow check is a pure
        input-shape check, requiring no I/O."""
        service, _, _, _ = _seeded()
        user_id = uuid4()

        with pytest.raises(CannotFollowSelfError):
            await service.execute(
                FollowDoctorInput(
                    follower_user_id=user_id, organization_id=uuid4(), followed_user_id=user_id
                )
            )

    async def test_unknown_followed_user_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(UserNotFoundForFollowError):
            await service.execute(
                FollowDoctorInput(
                    follower_user_id=uuid4(), organization_id=uuid4(), followed_user_id=uuid4()
                )
            )

    async def test_cross_tenant_followed_user_raises_not_found(self) -> None:
        service, _, users, _ = _seeded()
        followed_id = uuid4()
        users.add_user(make_user_summary(user_id=followed_id, organization_id=uuid4()))

        with pytest.raises(UserNotFoundForFollowError):
            await service.execute(
                FollowDoctorInput(
                    follower_user_id=uuid4(), organization_id=uuid4(), followed_user_id=followed_id
                )
            )

    async def test_idempotent_when_already_following(self) -> None:
        service, followers, users, uow = _seeded()
        followed_id, follower_id, org_id = uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=followed_id, organization_id=org_id))
        first = await service.execute(
            FollowDoctorInput(
                follower_user_id=follower_id, organization_id=org_id, followed_user_id=followed_id
            )
        )

        uow.committed = False
        second = await service.execute(
            FollowDoctorInput(
                follower_user_id=follower_id, organization_id=org_id, followed_user_id=followed_id
            )
        )
        assert second.follow_id == first.follow_id
        assert uow.committed is False

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, users, uow = _seeded()
        followed_id, org_id = uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=followed_id, organization_id=org_id))

        await service.execute(
            FollowDoctorInput(
                follower_user_id=uuid4(), organization_id=org_id, followed_user_id=followed_id
            )
        )
        assert uow.committed is True

    async def test_publishes_a_doctor_followed_event(self) -> None:
        service, _, users, uow = _seeded()
        followed_id, org_id = uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=followed_id, organization_id=org_id))

        await service.execute(
            FollowDoctorInput(
                follower_user_id=uuid4(), organization_id=org_id, followed_user_id=followed_id
            )
        )
        assert any(isinstance(e, DoctorFollowed) for e in uow.published_events)
