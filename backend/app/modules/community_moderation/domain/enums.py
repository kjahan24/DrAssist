"""Enums for the Community Moderation & Trust/Safety module.

`ModerationTargetType` is the one polymorphic target discriminator shared
by both `CommunityReport` (any of the six members is reportable) and the
content-moderation actions (`ReviewContent`/`RemoveContent`/
`RestoreContent`/`LockContent`, which only ever accept the four
content-shaped members — see `application/services/_target_resolution.py`)
— the same "one enum, no per-content-type duplication" shape
`app.modules.community_engagement.domain.enums.EngagementTargetType`
already establishes, extended with `COMMUNITY`/`USER` since reports (unlike
votes/saves) can target a community or a user directly, not just content.
"""

from enum import StrEnum


class ModerationTargetType(StrEnum):
    POST = "post"
    QUESTION = "question"
    ANSWER = "answer"
    COMMENT = "comment"
    COMMUNITY = "community"
    USER = "user"


class ReportReason(StrEnum):
    MEDICAL_MISINFORMATION = "medical_misinformation"
    SPAM = "spam"
    HARASSMENT = "harassment"
    ABUSE = "abuse"
    HATE_DISCRIMINATION = "hate_discrimination"
    PRIVACY_VIOLATION = "privacy_violation"
    IMPERSONATION = "impersonation"
    DANGEROUS_MEDICAL_ADVICE = "dangerous_medical_advice"
    SELF_HARM_CONCERN = "self_harm_concern"
    ILLEGAL_CONTENT = "illegal_content"
    OTHER = "other"


class ReportStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ReportPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModerationActionType(StrEnum):
    """Content-shaped verbs (`APPROVE`/`REMOVE`/`RESTRICT`/`LOCK`/`RESTORE`)
    apply only to `ModerationTargetType.POST`/`QUESTION`/`ANSWER`/`COMMENT`
    targets; user-shaped verbs (`WARN_USER`/`RESTRICT_USER`/`SUSPEND_USER`/
    `BAN_USER`) apply only to `ModerationTargetType.USER` targets — enforced
    by the application layer, not this enum itself. See
    `application/services/_target_resolution.py`'s own docstring."""

    APPROVE = "approve"
    REMOVE = "remove"
    RESTRICT = "restrict"
    LOCK = "lock"
    RESTORE = "restore"
    WARN_USER = "warn_user"
    RESTRICT_USER = "restrict_user"
    SUSPEND_USER = "suspend_user"
    BAN_USER = "ban_user"


class ContentModerationStatus(StrEnum):
    """The values `ModerationAction.previous_state`/`.new_state` carry for a
    content-shaped action — see `ModerationAction`'s own docstring for why
    "current status of a content item" is computed live from the latest
    `ModerationAction` row for that target rather than stored on a
    dedicated aggregate."""

    ACTIVE = "active"
    REMOVED = "removed"
    RESTRICTED = "restricted"
    LOCKED = "locked"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    REVOKED = "revoked"


class ModerationRestrictionType(StrEnum):
    WARNING = "warning"
    TEMPORARY_RESTRICTION = "temporary_restriction"
    SUSPENSION = "suspension"
    PERMANENT_BAN = "permanent_ban"
