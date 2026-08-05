"""Enums owned by the Community module's domain."""

from enum import StrEnum


class CommunityVisibility(StrEnum):
    """Who may discover/join a community. Enforced by
    `application.services.join_community_service.JoinCommunityService` —
    see that service's own docstring for exactly what each level permits
    at this foundation stage."""

    PUBLIC = "public"
    VERIFIED_ONLY = "verified_only"
    PRIVATE = "private"


class CommunityRole(StrEnum):
    """A member's standing within one specific community — ordered from
    least to most privileged. `OWNER` is assigned exactly once, to the
    community's creator (see `Community.create`); every other role is
    reachable only by a future moderation module this task explicitly
    excludes, so no role-change transition exists on `CommunityMember`
    yet (see that entity's own docstring)."""

    MEMBER = "member"
    MODERATOR = "moderator"
    ADMIN = "admin"
    OWNER = "owner"


class CommunityMemberStatus(StrEnum):
    """A membership row's current state. Only `ACTIVE` and `LEFT` are
    reachable via this task's own `JoinCommunityService`/
    `LeaveCommunityService` — `INVITED` (an admin-issued invitation
    awaiting acceptance) and `BLOCKED` (a moderation action) are modeled
    now so `CommunityMember`'s own state machine is complete for a future
    invitation/moderation module to build on, but nothing in this
    foundation constructs a member in either state — see
    `CommunityMember.create`'s own docstring.
    """

    ACTIVE = "active"
    INVITED = "invited"
    BLOCKED = "blocked"
    LEFT = "left"
