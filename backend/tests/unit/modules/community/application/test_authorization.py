"""Unit tests for `ensure_role_at_least` — the role-hierarchy
authorization helper shared by every mutating Community service."""

from uuid import uuid4

import pytest

from app.modules.community.application.services._authorization import ensure_role_at_least
from app.modules.community.domain.entities import CommunityMember
from app.modules.community.domain.enums import CommunityMemberStatus, CommunityRole
from app.modules.community.domain.exceptions import (
    CommunityMembershipNotFoundError,
    InsufficientCommunityRoleError,
)
from app.modules.community.domain.value_objects import CommunityId


def _member(
    role: CommunityRole, status: CommunityMemberStatus = CommunityMemberStatus.ACTIVE
) -> CommunityMember:
    return CommunityMember.create(
        community_id=CommunityId(uuid4()), user_id=uuid4(), role=role, status=status
    )


class TestEnsureRoleAtLeast:
    def test_none_member_raises_membership_not_found(self) -> None:
        with pytest.raises(CommunityMembershipNotFoundError):
            ensure_role_at_least(None, CommunityRole.ADMIN, community_id=uuid4(), user_id=uuid4())

    def test_inactive_member_raises_membership_not_found(self) -> None:
        member = _member(CommunityRole.OWNER, status=CommunityMemberStatus.LEFT)
        with pytest.raises(CommunityMembershipNotFoundError):
            ensure_role_at_least(
                member, CommunityRole.MEMBER, community_id=uuid4(), user_id=uuid4()
            )

    def test_exact_matching_role_passes(self) -> None:
        member = _member(CommunityRole.ADMIN)
        ensure_role_at_least(member, CommunityRole.ADMIN, community_id=uuid4(), user_id=uuid4())

    def test_higher_role_than_required_passes(self) -> None:
        member = _member(CommunityRole.OWNER)
        ensure_role_at_least(member, CommunityRole.ADMIN, community_id=uuid4(), user_id=uuid4())

    def test_lower_role_than_required_raises(self) -> None:
        member = _member(CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            ensure_role_at_least(member, CommunityRole.ADMIN, community_id=uuid4(), user_id=uuid4())

    def test_moderator_below_admin_requirement_raises(self) -> None:
        member = _member(CommunityRole.MODERATOR)
        with pytest.raises(InsufficientCommunityRoleError):
            ensure_role_at_least(member, CommunityRole.ADMIN, community_id=uuid4(), user_id=uuid4())

    def test_member_role_meets_member_requirement(self) -> None:
        member = _member(CommunityRole.MEMBER)
        ensure_role_at_least(member, CommunityRole.MEMBER, community_id=uuid4(), user_id=uuid4())

    def test_error_includes_the_required_role(self) -> None:
        member = _member(CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError) as exc_info:
            ensure_role_at_least(member, CommunityRole.OWNER, community_id=uuid4(), user_id=uuid4())
        assert exc_info.value.required_role == "owner"
