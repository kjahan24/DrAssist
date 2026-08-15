"""Enums owned by the Community Questions module's domain."""

from enum import StrEnum


class QuestionType(StrEnum):
    """What kind of question this is — purely descriptive/filterable
    (this task's own "Type" search filter), no type-specific validation
    or workflow branches on it anywhere in this module."""

    GENERAL = "general"
    CLINICAL = "clinical"
    PATIENT_EXPERIENCE = "patient_experience"
    TREATMENT_ADVICE = "treatment_advice"
    MEDICATION_QUESTION = "medication_question"
    DIAGNOSIS_DISCUSSION = "diagnosis_discussion"
    RESEARCH_QUESTION = "research_question"
    EDUCATIONAL_QUESTION = "educational_question"


class QuestionStatus(StrEnum):
    """A question's content lifecycle. Unlike
    `app.modules.community_posts.domain.enums.PostStatus` (`DRAFT ->
    PUBLISHED -> ARCHIVED`, deletion handled purely at the infrastructure
    level via `SoftDeleteMixin.deleted_at`), this task's own QUESTION
    STATUS section explicitly names five statuses including "Deleted" as
    a first-class status alongside "Archived" — so `CommunityQuestion`
    itself models deletion as a business-visible status transition
    (`CommunityQuestion.delete()`) rather than a hidden infrastructure
    concern; see that method's own docstring and
    `CommunityQuestionRepository`'s own docstring for why this repository
    has no `remove()` method the way `CommunityPostRepository` does.

    `CLOSED` and `REOPEN` back this task's own dedicated "Close Question"/
    "Reopen Question" FEATURES bullets — a distinct PUBLISHED<->CLOSED
    toggle pair, separate from the DRAFT/ARCHIVED<->PUBLISHED pair
    `publish()`/`archive()` manage (see `CommunityQuestion.close`/
    `.reopen`'s own docstrings)."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class QuestionVisibility(StrEnum):
    """Who may view a published question, independent of the parent
    community's own `CommunityVisibility` — the same three-tier shape
    `app.modules.community_posts.domain.enums.PostVisibility` already
    establishes, renamed here to fit a single question's own audience."""

    PUBLIC = "public"
    MEMBERS_ONLY = "members_only"
    PRIVATE = "private"
