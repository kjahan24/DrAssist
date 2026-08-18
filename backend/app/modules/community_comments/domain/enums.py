"""Enums owned by the Community Comments module's domain."""

from enum import StrEnum


class CommentStatus(StrEnum):
    """A comment/reply's content lifecycle — the same four-member shape
    `app.modules.community_answers.domain.enums.AnswerStatus` already
    establishes (deletion is a business-visible status transition, not
    an infrastructure-only soft delete; `restore()` always lands on
    `DRAFT`, never straight back to `PUBLISHED` — see
    `CommunityComment.restore`'s own docstring)."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"


class CommentTargetType(StrEnum):
    """Which existing community-content aggregate a *top-level* comment
    is attached to — this task's own DOMAIN section: "A comment/reply
    must belong to exactly one supported target: Post / Question /
    Answer / Parent Comment/Reply." A *reply* (any `CommunityComment`
    row with `parent_comment_id` set) still carries its own
    `target_type`/`target_id`, denormalized (copied) from its parent at
    creation time rather than re-resolved — see `CommunityComment`'s own
    module docstring for why, and `CreateReplyService`'s own docstring
    for where that copy happens.

    There is deliberately no database-level foreign key on
    `community_comments.target_id` — a single column cannot reference
    three different tables (`community_posts`/`community_questions`/
    `community_answers`) conditionally at the schema level. Existence and
    "open to new comments" (`PUBLISHED`) validation happens once, at
    write time, via the appropriate peer module's own public query port
    (`PostQueryPort`/`QuestionQueryPort`/`AnswerQueryPort`) — see
    `_target_resolution.py`'s own docstring."""

    POST = "post"
    QUESTION = "question"
    ANSWER = "answer"
