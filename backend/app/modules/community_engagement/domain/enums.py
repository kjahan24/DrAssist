"""Enums owned by the Community Engagement module's domain."""

from enum import StrEnum


class EngagementTargetType(StrEnum):
    """What kind of existing community-content aggregate a `Vote` or
    `SavedContent` row references — one shared enum for both, rather
    than two near-identical ones, matching this task's own "Do not
    duplicate voting logic for every content type" instruction.

    `SavedContent` never uses `COMMENT` — this task's own FEATURES list
    names "Save/unsave Post"/"Save/unsave Question"/"Save/unsave Answer"
    only, no "Save/unsave Comment" — `SaveContentService` rejects it
    explicitly (`UnsupportedSaveTargetTypeError`) rather than the enum
    itself being narrower, so both entities still share one vocabulary.

    There is deliberately no database-level foreign key on
    `votes.target_id`/`saved_content.target_id` — a single column cannot
    reference four different tables (`community_posts`/
    `community_questions`/`community_answers`/`community_comments`)
    conditionally at the schema level. Existence, tenant ownership, and
    "open to engagement" (`PUBLISHED`) validation happens once, at write
    time, via the appropriate peer module's own public query port
    (`PostQueryPort`/`QuestionQueryPort`/`AnswerQueryPort`/
    `CommentQueryPort`) — the same design
    `app.modules.community_comments.domain.enums.CommentTargetType`
    already establishes for itself.
    """

    POST = "post"
    QUESTION = "question"
    ANSWER = "answer"
    COMMENT = "comment"


class VoteType(StrEnum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"


class FollowTargetType(StrEnum):
    """Which of the three separate follower tables (`topic_followers`/
    `community_followers`/`doctor_followers` — this task's own DATABASE
    section names them as three distinct tables, not one generic
    `follows` table, so this enum is *not* a stored column anywhere; it
    only discriminates which repository `ListFollowersService`/
    `ListFollowingService` dispatch to) a follow relationship belongs
    to."""

    TOPIC = "topic"
    COMMUNITY = "community"
    DOCTOR = "doctor"
