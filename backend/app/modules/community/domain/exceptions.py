"""Domain exceptions for the Community module.

Each names the invariant it protects, not the eventual HTTP outcome —
`app.middlewares.error_handler` maps every `DomainError` subclass to an
HTTP status by a codebase-wide naming convention (`"NotFound"` -> 404;
`"Duplicate"`/`"AlreadyExists"` -> 409; everything else -> 422). See
`docs/backend-architecture/06_configuration_logging_exceptions.md` and
that handler's own module docstring for the exact heuristic.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class CommunityNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("community name must not be blank")


class InvalidCommunitySlugError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value!r} is not a valid community slug")
        self.value = value


class CommunityDescriptionRequiredError(DomainError):
    """Raised when a blank string is passed for a description — a caller
    with nothing to say must pass `None`, not an empty/whitespace-only
    string; see `CommunityDescription`'s own docstring."""

    def __init__(self) -> None:
        super().__init__("community description must not be blank; omit it entirely instead")


class CommunityDescriptionTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        super().__init__(f"community description must not exceed {max_length} characters")
        self.max_length = max_length


class CommunityNameTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        super().__init__(f"community name must not exceed {max_length} characters")
        self.max_length = max_length


class DuplicateCommunitySlugError(DomainError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"a community with slug {slug!r} already exists in this organization")
        self.slug = slug


class CommunityNotFoundError(DomainError):
    def __init__(self, community_id: UUID) -> None:
        super().__init__(f"no community found with id {community_id}")
        self.community_id = community_id


class CommunityMembershipNotFoundError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        super().__init__(f"user {user_id} has no membership in community {community_id}")
        self.community_id = community_id
        self.user_id = user_id


class CommunityMembershipAlreadyExistsError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        super().__init__(f"user {user_id} is already an active member of community {community_id}")
        self.community_id = community_id
        self.user_id = user_id


class CommunityMemberBlockedError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        super().__init__(f"user {user_id} is blocked from community {community_id}")
        self.community_id = community_id
        self.user_id = user_id


class PrivateCommunityJoinRequiresInviteError(DomainError):
    """`PRIVATE`/`VERIFIED_ONLY` communities cannot be joined directly —
    see `JoinCommunityService`'s own docstring for the full reasoning."""

    def __init__(self, community_id: UUID) -> None:
        super().__init__(f"community {community_id} requires an invitation to join")
        self.community_id = community_id


class InsufficientCommunityRoleError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID, required_role: str) -> None:
        super().__init__(
            f"user {user_id} does not have at least {required_role!r} role "
            f"in community {community_id}"
        )
        self.community_id = community_id
        self.user_id = user_id
        self.required_role = required_role


class CommunityOwnerRequiredError(DomainError):
    """A community must always retain at least one `OWNER` member — see
    `LeaveCommunityService`'s own docstring."""

    def __init__(self, community_id: UUID) -> None:
        super().__init__(f"community {community_id} must retain at least one owner")
        self.community_id = community_id
