"""Tests for the `CommunityMember` aggregate root."""

from uuid import uuid4

from app.modules.community.domain.entities import CommunityMember
from app.modules.community.domain.enums import CommunityMemberStatus, CommunityRole
from app.modules.community.domain.events import CommunityMemberJoined, CommunityMemberLeft
from app.modules.community.domain.value_objects import CommunityId


class TestCommunityMemberCreate:
    def test_sets_required_fields(self) -> None:
        community_id = CommunityId(uuid4())
        user_id = uuid4()
        member = CommunityMember.create(community_id=community_id, user_id=user_id)
        assert member.community_id == community_id
        assert member.user_id == user_id

    def test_defaults_to_member_role(self) -> None:
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        assert member.role is CommunityRole.MEMBER

    def test_defaults_to_active_status(self) -> None:
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        assert member.status is CommunityMemberStatus.ACTIVE

    def test_accepts_explicit_role(self) -> None:
        member = CommunityMember.create(
            community_id=CommunityId(uuid4()), user_id=uuid4(), role=CommunityRole.OWNER
        )
        assert member.role is CommunityRole.OWNER

    def test_accepts_explicit_status(self) -> None:
        member = CommunityMember.create(
            community_id=CommunityId(uuid4()), user_id=uuid4(), status=CommunityMemberStatus.INVITED
        )
        assert member.status is CommunityMemberStatus.INVITED

    def test_sets_joined_at(self) -> None:
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        assert member.joined_at is not None

    def test_assigns_a_unique_id(self) -> None:
        first = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        second = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        assert first.id != second.id

    def test_active_member_records_a_joined_event(self) -> None:
        community_id = CommunityId(uuid4())
        user_id = uuid4()
        member = CommunityMember.create(
            community_id=community_id, user_id=user_id, role=CommunityRole.MEMBER
        )
        events = member.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityMemberJoined)
        assert event.community_id == community_id.value
        assert event.user_id == user_id
        assert event.role == "member"

    def test_invited_member_records_no_joined_event(self) -> None:
        member = CommunityMember.create(
            community_id=CommunityId(uuid4()), user_id=uuid4(), status=CommunityMemberStatus.INVITED
        )
        assert member.pull_events() == []

    def test_blocked_member_records_no_joined_event(self) -> None:
        member = CommunityMember.create(
            community_id=CommunityId(uuid4()), user_id=uuid4(), status=CommunityMemberStatus.BLOCKED
        )
        assert member.pull_events() == []


class TestCommunityMemberLeave:
    def test_sets_status_to_left(self) -> None:
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        member.leave()
        assert member.status is CommunityMemberStatus.LEFT

    def test_updates_updated_at(self) -> None:
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        before = member.updated_at
        member.leave()
        assert member.updated_at >= before

    def test_records_a_left_event(self) -> None:
        community_id = CommunityId(uuid4())
        user_id = uuid4()
        member = CommunityMember.create(community_id=community_id, user_id=user_id)
        member.pull_events()
        member.leave()
        events = member.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityMemberLeft)
        assert event.community_id == community_id.value
        assert event.user_id == user_id

    def test_calling_leave_twice_still_records_two_events(self) -> None:
        """`leave()` has no idempotency guard — calling it on an already
        `LEFT` member still records a second `CommunityMemberLeft` event.
        Nothing in this module calls `leave()` twice in a row (the
        application layer's own `LeaveCommunityService` always checks
        `status is ACTIVE` first), so this documents actual behavior
        rather than a designed invariant."""
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        member.pull_events()
        member.leave()
        member.leave()
        assert len(member.pull_events()) == 2


class TestCommunityMemberRejoin:
    def test_sets_status_to_active(self) -> None:
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        member.leave()
        member.rejoin()
        assert member.status is CommunityMemberStatus.ACTIVE

    def test_refreshes_joined_at(self) -> None:
        member = CommunityMember.create(community_id=CommunityId(uuid4()), user_id=uuid4())
        member.leave()
        original_joined_at = member.joined_at
        member.rejoin()
        assert member.joined_at >= original_joined_at

    def test_records_a_joined_event(self) -> None:
        community_id = CommunityId(uuid4())
        user_id = uuid4()
        member = CommunityMember.create(community_id=community_id, user_id=user_id)
        member.leave()
        member.pull_events()
        member.rejoin()
        events = member.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityMemberJoined)

    def test_accepting_an_invite_also_transitions_to_active(self) -> None:
        member = CommunityMember.create(
            community_id=CommunityId(uuid4()), user_id=uuid4(), status=CommunityMemberStatus.INVITED
        )
        member.rejoin()
        assert member.status is CommunityMemberStatus.ACTIVE

    def test_preserves_role(self) -> None:
        member = CommunityMember.create(
            community_id=CommunityId(uuid4()), user_id=uuid4(), role=CommunityRole.MODERATOR
        )
        member.leave()
        member.rejoin()
        assert member.role is CommunityRole.MODERATOR
