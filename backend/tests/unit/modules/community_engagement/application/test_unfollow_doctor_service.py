"""Unit tests for `UnfollowDoctorService` — unconditionally idempotent."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import UnfollowDoctorInput
from app.modules.community_engagement.application.services.unfollow_doctor_service import (
    UnfollowDoctorService,
)
from app.modules.community_engagement.domain.entities import DoctorFollower
from app.modules.community_engagement.domain.events import DoctorUnfollowed
from tests.unit.modules.community_engagement.application.fakes import (
    FakeDoctorFollowerRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[UnfollowDoctorService, FakeDoctorFollowerRepository, FakeUnitOfWork]:
    followers = FakeDoctorFollowerRepository()
    uow = FakeUnitOfWork()
    service = UnfollowDoctorService(doctor_follower_repository=followers, unit_of_work=uow)
    return service, followers, uow


class TestUnfollowDoctor:
    async def test_removes_an_existing_follow(self) -> None:
        service, followers, _ = _seeded()
        follower_id, followed_id = uuid4(), uuid4()
        follower = DoctorFollower.create(
            follower_user_id=follower_id, organization_id=uuid4(), followed_user_id=followed_id
        )
        await followers.add(follower)

        await service.execute(
            UnfollowDoctorInput(follower_user_id=follower_id, followed_user_id=followed_id)
        )
        assert await followers.get_follow(follower_id, followed_id) is None

    async def test_unfollowing_someone_never_followed_is_a_silent_no_op(self) -> None:
        service, _, uow = _seeded()
        await service.execute(
            UnfollowDoctorInput(follower_user_id=uuid4(), followed_user_id=uuid4())
        )
        assert uow.committed is False

    async def test_commits_the_unit_of_work_when_a_follow_is_removed(self) -> None:
        service, followers, uow = _seeded()
        follower_id, followed_id = uuid4(), uuid4()
        follower = DoctorFollower.create(
            follower_user_id=follower_id, organization_id=uuid4(), followed_user_id=followed_id
        )
        await followers.add(follower)

        await service.execute(
            UnfollowDoctorInput(follower_user_id=follower_id, followed_user_id=followed_id)
        )
        assert uow.committed is True

    async def test_publishes_a_doctor_unfollowed_event(self) -> None:
        service, followers, uow = _seeded()
        follower_id, followed_id = uuid4(), uuid4()
        follower = DoctorFollower.create(
            follower_user_id=follower_id, organization_id=uuid4(), followed_user_id=followed_id
        )
        await followers.add(follower)

        await service.execute(
            UnfollowDoctorInput(follower_user_id=follower_id, followed_user_id=followed_id)
        )
        assert any(isinstance(e, DoctorUnfollowed) for e in uow.published_events)
