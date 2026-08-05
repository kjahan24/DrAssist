"""Tests for the Community module's domain enums."""

from enum import StrEnum

from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)


class TestCommunityVisibility:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(CommunityVisibility, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(CommunityVisibility) == 3

    def test_public_value(self) -> None:
        assert CommunityVisibility.PUBLIC.value == "public"

    def test_verified_only_value(self) -> None:
        assert CommunityVisibility.VERIFIED_ONLY.value == "verified_only"

    def test_private_value(self) -> None:
        assert CommunityVisibility.PRIVATE.value == "private"

    def test_members_are_strings(self) -> None:
        for member in CommunityVisibility:
            assert isinstance(member, str)


class TestCommunityRole:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(CommunityRole, StrEnum)

    def test_has_exactly_four_members(self) -> None:
        assert len(CommunityRole) == 4

    def test_member_value(self) -> None:
        assert CommunityRole.MEMBER.value == "member"

    def test_moderator_value(self) -> None:
        assert CommunityRole.MODERATOR.value == "moderator"

    def test_admin_value(self) -> None:
        assert CommunityRole.ADMIN.value == "admin"

    def test_owner_value(self) -> None:
        assert CommunityRole.OWNER.value == "owner"

    def test_members_are_strings(self) -> None:
        for member in CommunityRole:
            assert isinstance(member, str)


class TestCommunityMemberStatus:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(CommunityMemberStatus, StrEnum)

    def test_has_exactly_four_members(self) -> None:
        assert len(CommunityMemberStatus) == 4

    def test_active_value(self) -> None:
        assert CommunityMemberStatus.ACTIVE.value == "active"

    def test_invited_value(self) -> None:
        assert CommunityMemberStatus.INVITED.value == "invited"

    def test_blocked_value(self) -> None:
        assert CommunityMemberStatus.BLOCKED.value == "blocked"

    def test_left_value(self) -> None:
        assert CommunityMemberStatus.LEFT.value == "left"

    def test_members_are_strings(self) -> None:
        for member in CommunityMemberStatus:
            assert isinstance(member, str)
