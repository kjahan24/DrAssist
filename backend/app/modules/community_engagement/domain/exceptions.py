"""Domain exceptions for the Community Engagement module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422 (well-formed request,
semantically invalid). See that module's own docstring for the full
heuristic.

`VoteTargetNotFoundError`/`SaveTargetNotFoundError` are raised for *both*
"the target genuinely doesn't exist" and "the target belongs to a
different organization" (this task's own "Tenant isolation" DOMAIN rule)
— deliberately the same exception, same message shape, for both cases:
a cross-tenant target should be indistinguishable from a nonexistent one
to the caller, so a user can never probe whether a given id exists in
*someone else's* organization. See `_target_resolution.py`'s own
docstring.
"""

from uuid import UUID

from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.shared.domain.exceptions import DomainError


class VoteTargetNotFoundError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"No vote target found with id {target_id}.")


class VoteTargetNotAcceptingVotesError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"Target {target_id} is not open to voting.")


class SaveTargetNotFoundError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"No save target found with id {target_id}.")


class SaveTargetNotAcceptingSavesError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"Target {target_id} is not open to saving.")


class UnsupportedSaveTargetTypeError(DomainError):
    def __init__(self, target_type: EngagementTargetType) -> None:
        self.target_type = target_type
        super().__init__(f"Content of type {target_type.value!r} cannot be saved.")


class TopicNotFoundForFollowError(DomainError):
    def __init__(self, topic_id: UUID) -> None:
        self.topic_id = topic_id
        super().__init__(f"No topic found with id {topic_id}.")


class CommunityNotFoundForFollowError(DomainError):
    def __init__(self, community_id: UUID) -> None:
        self.community_id = community_id
        super().__init__(f"No community found with id {community_id}.")


class UserNotFoundForFollowError(DomainError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"No user found with id {user_id}.")


class CannotFollowSelfError(DomainError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} cannot follow themselves.")
