"""Direct unit tests for `_authorization.py` — the role-hierarchy and
viewability helpers shared by every mutating/reading Community Comments
service. Exercises every branch directly, since not every branch is
reachable through every individual service's own test file."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityMemberStatus, CommunityRole
from app.modules.community_comments.application.services._authorization import (
    ensure_can_author_action,
    ensure_can_create,
    ensure_can_view,
    ensure_can_view_target,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.exceptions import (
    CommentMembershipRequiredError,
    CommentNotViewableError,
    InsufficientCommentRoleError,
    TargetNotViewableForCommentError,
)
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import make_member_summary


def _comment(**overrides: object) -> CommunityComment:
    defaults: dict[str, object] = {
        "target_type": CommentTargetType.POST,
        "target_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": None,
        "author_id": uuid4(),
        "body": CommentBody("Body."),
    }
    defaults.update(overrides)
    return CommunityComment.create(**defaults)  # type: ignore[arg-type]


class TestEnsureCanCreate:
    def test_active_member_is_allowed(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        member = make_member_summary(community_id=community_id, user_id=user_id)
        ensure_can_create(member, community_id=community_id, user_id=user_id)

    def test_no_membership_raises(self) -> None:
        with pytest.raises(CommentMembershipRequiredError):
            ensure_can_create(None, community_id=uuid4(), user_id=uuid4())

    def test_inactive_membership_raises(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=user_id, status=CommunityMemberStatus.BLOCKED
        )
        with pytest.raises(CommentMembershipRequiredError):
            ensure_can_create(member, community_id=community_id, user_id=user_id)


class TestEnsureCanAuthorAction:
    def test_the_author_is_always_allowed(self) -> None:
        author_id, community_id = uuid4(), uuid4()
        ensure_can_author_action(
            None, community_id=community_id, user_id=author_id, author_id=author_id
        )

    def test_moderator_is_allowed_for_someone_elses_comment(self) -> None:
        community_id, moderator_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
        )
        ensure_can_author_action(
            member, community_id=community_id, user_id=moderator_id, author_id=author_id
        )

    def test_admin_is_allowed(self) -> None:
        community_id, admin_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=admin_id, role=CommunityRole.ADMIN
        )
        ensure_can_author_action(
            member, community_id=community_id, user_id=admin_id, author_id=author_id
        )

    def test_owner_is_allowed(self) -> None:
        community_id, owner_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=owner_id, role=CommunityRole.OWNER
        )
        ensure_can_author_action(
            member, community_id=community_id, user_id=owner_id, author_id=author_id
        )

    def test_plain_member_raises_for_someone_elses_comment(self) -> None:
        community_id, member_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(community_id=community_id, user_id=member_id)
        with pytest.raises(InsufficientCommentRoleError):
            ensure_can_author_action(
                member, community_id=community_id, user_id=member_id, author_id=author_id
            )

    def test_no_membership_raises_for_someone_elses_comment(self) -> None:
        with pytest.raises(CommentMembershipRequiredError):
            ensure_can_author_action(None, community_id=uuid4(), user_id=uuid4(), author_id=uuid4())


class TestEnsureCanView:
    def test_published_comment_is_viewable_with_no_member_and_no_user(self) -> None:
        comment = _comment()
        comment.publish()
        ensure_can_view(comment, None, user_id=None)

    def test_draft_comment_raises_for_a_stranger(self) -> None:
        comment = _comment()
        with pytest.raises(CommentNotViewableError):
            ensure_can_view(comment, None, user_id=uuid4())

    def test_draft_comment_viewable_by_its_own_author(self) -> None:
        comment = _comment()
        ensure_can_view(comment, None, user_id=comment.author_id)

    def test_draft_comment_viewable_by_a_moderator(self) -> None:
        comment = _comment()
        member = make_member_summary(
            community_id=comment.community_id, role=CommunityRole.MODERATOR
        )
        ensure_can_view(comment, member, user_id=uuid4())

    def test_draft_comment_raises_for_a_plain_member(self) -> None:
        comment = _comment()
        member = make_member_summary(community_id=comment.community_id, role=CommunityRole.MEMBER)
        with pytest.raises(CommentNotViewableError):
            ensure_can_view(comment, member, user_id=uuid4())

    def test_archived_comment_follows_the_same_rule_as_draft(self) -> None:
        comment = _comment()
        comment.archive()
        with pytest.raises(CommentNotViewableError):
            ensure_can_view(comment, None, user_id=uuid4())

    def test_deleted_comment_follows_the_same_rule_as_draft(self) -> None:
        comment = _comment()
        comment.delete()
        with pytest.raises(CommentNotViewableError):
            ensure_can_view(comment, None, user_id=uuid4())


class TestEnsureCanViewTarget:
    def test_public_target_is_viewable_with_no_member_and_no_user(self) -> None:
        ensure_can_view_target(
            target_id=uuid4(),
            visibility_value="public",
            target_author_id=uuid4(),
            member=None,
            user_id=None,
        )

    def test_members_only_target_raises_for_no_member(self) -> None:
        target_id = uuid4()
        with pytest.raises(TargetNotViewableForCommentError):
            ensure_can_view_target(
                target_id=target_id,
                visibility_value="members_only",
                target_author_id=uuid4(),
                member=None,
                user_id=uuid4(),
            )

    def test_members_only_target_allowed_for_active_member(self) -> None:
        member = make_member_summary(status=CommunityMemberStatus.ACTIVE)
        ensure_can_view_target(
            target_id=uuid4(),
            visibility_value="members_only",
            target_author_id=uuid4(),
            member=member,
            user_id=uuid4(),
        )

    def test_private_target_allowed_for_its_own_author(self) -> None:
        author_id = uuid4()
        ensure_can_view_target(
            target_id=uuid4(),
            visibility_value="private",
            target_author_id=author_id,
            member=None,
            user_id=author_id,
        )

    def test_private_target_raises_for_a_plain_member(self) -> None:
        target_id = uuid4()
        member = make_member_summary(role=CommunityRole.MEMBER)
        with pytest.raises(TargetNotViewableForCommentError):
            ensure_can_view_target(
                target_id=target_id,
                visibility_value="private",
                target_author_id=uuid4(),
                member=member,
                user_id=uuid4(),
            )

    def test_private_target_allowed_for_a_moderator(self) -> None:
        member = make_member_summary(role=CommunityRole.MODERATOR)
        ensure_can_view_target(
            target_id=uuid4(),
            visibility_value="private",
            target_author_id=uuid4(),
            member=member,
            user_id=uuid4(),
        )

    def test_private_target_with_unknown_author_raises_for_a_plain_member(self) -> None:
        """When `target_author_id` is `None` (an anonymous target — see
        `ResolvedTarget`'s own docstring), the caller can never
        self-identify as the author, even if they secretly are one."""
        target_id = uuid4()
        member = make_member_summary(role=CommunityRole.MEMBER)
        with pytest.raises(TargetNotViewableForCommentError):
            ensure_can_view_target(
                target_id=target_id,
                visibility_value="private",
                target_author_id=None,
                member=member,
                user_id=uuid4(),
            )
