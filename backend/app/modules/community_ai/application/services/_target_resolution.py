"""Resolves a `(CommunityContentTargetType, target_id)` pair to the
information every AI analysis service actually needs: which organization
and community it belongs to (tenant isolation / membership-based
visibility), its title/text (what gets embedded or sent to the AI
provider), and whether the caller may see it at all.

One resolver for all four target types, reusing each peer module's own
already-public, read-only query port — the same "no per-content-type
duplication" shape `app.modules.community_engagement.application.services
._target_resolution.resolve_engagement_target` already establishes.

A `COMMENT` target means "the reply thread rooted at this comment" (this
task's own "Long discussion threads" summarization target) — `text` is
every `PUBLISHED` comment in the thread (root plus replies), joined in
`(depth, created_at)` order via the module-level `get_thread_summaries`
extension added to `CommentQueryPort` for this task; deleted/archived
replies are silently excluded from the joined text, satisfying "Respect
deleted, archived and restricted content" for thread analysis
specifically.

`CommunityCommentSummaryDTO` carries no `visibility` field of its own
(unlike posts/questions/answers) — a comment's visibility is inherited
from whichever post/question it targets, which this resolver does not
re-resolve a second hop to fetch. Comment/thread analysis is therefore
authorized on tenant/community-membership grounds only, not the parent
target's own finer-grained visibility — a disclosed, deliberate
simplification; see `_authorization.py`'s own docstring.

Cross-tenant existence collapses into "not found," never a distinct
error — the same deliberate anti-enumeration posture
`app.modules.community_engagement.application.services._target_resolution`
's own docstring establishes.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.dto import CommentStatus
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort

_PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class ResolvedAnalysisTarget:
    """`author_id` is whatever the target's own public port already
    returns — kept only for the `PRIVATE`-visibility "is the requester
    the author" authorization check in `_authorization.py`. It is never
    included in an AI prompt (no target type's prompt text interpolates
    author identity at all, anonymous or not) and never returned in any
    response DTO — this field exists purely for that one internal check.

    For `POST`/`QUESTION`, this is always the real author id (neither
    `PostFacade` nor `QuestionFacade` masks it). For `ANSWER`/`COMMENT`,
    `AnswerFacade`/`CommentFacade` already mask it to `None` for
    anonymous content *before* this resolver ever sees it — a disclosed,
    inherited limitation: an anonymous author cannot use the "I am the
    author" exception for their own `PRIVATE` answer/comment through this
    module (they would still be authorized via moderator rank, if
    applicable). Fixing that would mean changing two already-complete
    modules' own masking behavior for every other read path that depends
    on it too, not something this module's own scope warrants."""

    organization_id: UUID
    community_id: UUID
    title: str | None
    text: str
    author_id: UUID | None
    is_anonymous: bool
    visibility_value: str | None
    is_published: bool


async def resolve_analysis_target(
    target_type: CommunityContentTargetType,
    target_id: UUID,
    *,
    post_query_port: PostQueryPort,
    question_query_port: QuestionQueryPort,
    answer_query_port: AnswerQueryPort,
    comment_query_port: CommentQueryPort,
) -> ResolvedAnalysisTarget | None:
    if target_type is CommunityContentTargetType.POST:
        post = await post_query_port.get_post_summary(target_id)
        if post is None:
            return None
        return ResolvedAnalysisTarget(
            organization_id=post.organization_id,
            community_id=post.community_id,
            title=post.title,
            text=post.body,
            author_id=post.author_id,
            is_anonymous=post.is_anonymous,
            visibility_value=post.visibility.value,
            is_published=post.status.value == _PUBLISHED,
        )

    if target_type is CommunityContentTargetType.QUESTION:
        question = await question_query_port.get_question_summary(target_id)
        if question is None:
            return None
        return ResolvedAnalysisTarget(
            organization_id=question.organization_id,
            community_id=question.community_id,
            title=question.title,
            text=question.body,
            author_id=question.author_id,
            is_anonymous=question.is_anonymous,
            visibility_value=question.visibility.value,
            is_published=question.status.value == _PUBLISHED,
        )

    if target_type is CommunityContentTargetType.ANSWER:
        answer = await answer_query_port.get_answer_summary(target_id)
        if answer is None:
            return None
        return ResolvedAnalysisTarget(
            organization_id=answer.organization_id,
            community_id=answer.community_id,
            title=None,
            text=answer.body,
            author_id=answer.author_id,
            is_anonymous=answer.is_anonymous,
            visibility_value=answer.visibility.value,
            is_published=answer.status.value == _PUBLISHED,
        )

    # CommunityContentTargetType.COMMENT — the reply thread rooted here.
    root = await comment_query_port.get_comment_summary(target_id)
    if root is None:
        return None
    thread = await comment_query_port.get_thread_summaries(target_id)
    published_bodies = [c.body for c in thread if c.status is CommentStatus.PUBLISHED]
    return ResolvedAnalysisTarget(
        organization_id=root.organization_id,
        community_id=root.community_id,
        title=None,
        text="\n\n".join(published_bodies),
        author_id=None,
        is_anonymous=False,
        visibility_value=None,
        is_published=root.status.value == _PUBLISHED,
    )
