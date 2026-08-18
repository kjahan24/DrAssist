"""Enums owned by the Community Answers module's domain."""

from enum import StrEnum


class AnswerStatus(StrEnum):
    """An answer's content lifecycle. Mirrors `app.modules
    .community_questions.domain.enums.QuestionStatus` in modeling
    deletion as a business-visible status transition
    (`CommunityAnswer.delete()`) rather than an infrastructure-only soft
    delete — this task's own ANSWER STATUS section explicitly names
    "Deleted" as one of four first-class statuses. Unlike `QuestionStatus`,
    there is no `CLOSED` member: this task's own FEATURES list names
    "Restore Answer" (not "Close"/"Reopen") as the archived/deleted
    recovery action — see `CommunityAnswer.restore`'s own docstring."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class AnswerVisibility(StrEnum):
    """Who may view a published answer, independent of the parent
    community's own `CommunityVisibility` — the same three-tier shape
    `app.modules.community_questions.domain.enums.QuestionVisibility`
    already establishes, renamed here to fit a single answer's own
    audience."""

    PUBLIC = "public"
    MEMBERS_ONLY = "members_only"
    PRIVATE = "private"
