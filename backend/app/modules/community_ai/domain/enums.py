"""Enums for the Community AI Features module.

`CommunityContentTargetType` is the one polymorphic target discriminator
every AI analysis operates against — the same "one enum, no per-content-
type duplication" shape `app.modules.community_engagement.domain.enums
.EngagementTargetType` already establishes. It has no `COMMUNITY`/`USER`
members (unlike `app.modules.community_moderation.domain.enums
.ModerationTargetType`) — AI analysis only ever runs against actual
discussion content, never a community or a user, matching this task's own
FEATURES list (Posts/Questions/Answers/threads only). A `COMMENT` target
means "the reply thread rooted at this comment" for summarization (this
task's own "Long discussion threads" summary target) — see
`_target_resolution.py`'s own docstring.
"""

from enum import StrEnum


class CommunityContentTargetType(StrEnum):
    POST = "post"
    QUESTION = "question"
    ANSWER = "answer"
    COMMENT = "comment"


class AIAnalysisType(StrEnum):
    SUMMARY = "summary"
    SIMILAR_DISCUSSIONS = "similar_discussions"
    RESOURCE_RECOMMENDATION = "resource_recommendation"
    MISINFORMATION = "misinformation"


class AIAnalysisStatus(StrEnum):
    """No module before this one has ever needed a job-execution status
    (every prior AI-feature module in this codebase calls its provider
    synchronously, inline, and returns without persisting anything) — see
    `entities.py`'s own module docstring for why this module is the first
    to need one."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MisinformationRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceType(StrEnum):
    ARTICLE = "article"
    GUIDELINE = "guideline"
    RESEARCH_PAPER = "research_paper"
    WEBSITE = "website"
    ORGANIZATION = "organization"
    OTHER = "other"
