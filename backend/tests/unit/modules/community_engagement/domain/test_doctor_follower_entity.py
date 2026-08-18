"""Tests for the `DoctorFollower` aggregate root."""

from uuid import uuid4

from app.modules.community_engagement.domain.entities import DoctorFollower
from app.modules.community_engagement.domain.events import DoctorFollowed, DoctorUnfollowed


def _follower(**overrides: object) -> DoctorFollower:
    defaults: dict[str, object] = {
        "follower_user_id": uuid4(),
        "organization_id": uuid4(),
        "followed_user_id": uuid4(),
    }
    defaults.update(overrides)
    return DoctorFollower.create(**defaults)  # type: ignore[arg-type]


class TestDoctorFollowerCreate:
    def test_sets_required_fields(self) -> None:
        follower_user_id = uuid4()
        organization_id = uuid4()
        followed_user_id = uuid4()
        follower = DoctorFollower.create(
            follower_user_id=follower_user_id,
            organization_id=organization_id,
            followed_user_id=followed_user_id,
        )
        assert follower.follower_user_id == follower_user_id
        assert follower.organization_id == organization_id
        assert follower.followed_user_id == followed_user_id

    def test_assigns_a_unique_id(self) -> None:
        first = _follower()
        second = _follower()
        assert first.id != second.id

    def test_does_not_itself_prevent_self_follow(self) -> None:
        """Structural note: `DoctorFollower.create` performs no
        self-follow validation — that check belongs to
        `FollowDoctorService` (an application-layer concern needing no
        entity-level enforcement here), backed by the database's own
        `ck_doctor_followers_no_self_follow` constraint as a safety net.
        This test documents that boundary rather than asserting a
        guard that deliberately does not exist at this layer."""
        user_id = uuid4()
        follower = DoctorFollower.create(
            follower_user_id=user_id, organization_id=uuid4(), followed_user_id=user_id
        )
        assert follower.follower_user_id == follower.followed_user_id

    def test_records_a_doctor_followed_event(self) -> None:
        follower_user_id = uuid4()
        followed_user_id = uuid4()
        follower = _follower(follower_user_id=follower_user_id, followed_user_id=followed_user_id)
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DoctorFollowed)
        assert event.doctor_follower_id == follower.id
        assert event.follower_user_id == follower_user_id
        assert event.followed_user_id == followed_user_id

    def test_pull_events_drains_the_queue(self) -> None:
        follower = _follower()
        follower.pull_events()
        assert follower.pull_events() == []


class TestDoctorFollowerMarkRemoved:
    def test_records_a_doctor_unfollowed_event(self) -> None:
        follower_user_id = uuid4()
        followed_user_id = uuid4()
        follower = _follower(follower_user_id=follower_user_id, followed_user_id=followed_user_id)
        follower.pull_events()
        follower.mark_removed()
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DoctorUnfollowed)
        assert event.doctor_follower_id == follower.id
        assert event.follower_user_id == follower_user_id
        assert event.followed_user_id == followed_user_id
