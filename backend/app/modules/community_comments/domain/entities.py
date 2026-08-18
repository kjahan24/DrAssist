"""Community Comments module aggregate roots: CommunityComment,
CommunityCommentRevision, CommunityCommentAttachment.

Every reference to another aggregate, including cross-module ones
(`target_id` -> CommunityPost/CommunityQuestion/CommunityAnswer,
`community_id` -> Community, `topic_id` -> MedicalTopic, `author_id`/
`updated_by` -> User, `document_id` -> MedicalDocument), is by ID only,
never by object reference — the same rule
`app.modules.community_answers.domain.entities` already follows.
Cross-module ID references are validated by the application layer via
that peer module's own public query port (`PostQueryPort`/
`QuestionQueryPort`/`AnswerQueryPort`/`CommunityQueryPort`/
`DocumentQueryPort`), never by importing across `domain/` packages.

A **reply is a `CommunityComment` row like any other**, not a distinct
entity type: `parent_comment_id` (nullable, self-referential) is `None`
for a top-level comment and the immediate parent's own `id` for a reply
at any depth — matching this task's own diagram ("Comment -> Reply ->
Reply"). This single-entity design avoids duplicating the entire
lifecycle/authorization/revision/attachment machinery for what would
otherwise be a near-identical "Reply" entity; the APPLICATION layer still
exposes distinct `CreateComment`/`CreateReply` use cases (genuinely
different: target-based vs parent-based), matching this task's own
literal feature list, while `Update`/`Delete`/`Restore`/`Publish`/
`Archive` operate uniformly on either — see
`app.modules.community_comments.application.services`'s own package
docstring for the full reasoning.

`target_type`/`target_id`/`community_id`/`organization_id`/`topic_id`
are all stored directly on *every* row, including replies (denormalized
from the target at top-level-comment creation time, or copied from the
parent at reply creation time) — the same "tenant id stored directly on
the tenant-scoped row" shape `CommunityAnswer.community_id`/
`.organization_id`/`.topic_id` already establishes for itself, here
additionally letting "all comments under Post X, regardless of nesting
depth" be answered with a flat, indexed `WHERE` clause instead of a
recursive parent-chain walk. `topic_id` is nullable because
`CommunityPost` has no topic concept at all (only Questions/Answers do)
— see `CommentTargetType`'s own docstring.

`root_comment_id` (never null; equals `self.id` for a top-level comment,
copied from the parent's own `root_comment_id` for a reply at any depth)
and `depth` (0 for a top-level comment, `parent.depth + 1` for a reply)
are both set once at creation and never mutated afterward — together
they let `get_thread()` fetch an entire bounded-depth conversation with
one flat, indexed `WHERE root_comment_id = X AND depth <= N` query, with
no recursive CTE — see `CommunityCommentRepository.get_thread`'s own
docstring and this task's own "Do not use unbounded recursive queries"/
"Use safe bounded-depth thread retrieval" instructions.

"No invalid circular parent relationships" (this task's own DOMAIN
section) is enforced *structurally*, not by a runtime cycle-detection
walk: `parent_comment_id` is written exactly once, at construction
(`create()` always sets it to `None`; `create_reply()` always sets it to
`parent.id`), and this class exposes no "reparent" mutator anywhere — a
parent must already exist (`CreateReplyService` loads it via
`CommunityCommentRepository.get_by_id` before calling `create_reply()`)
before a child can reference it, so a forward-only, append-only
reference graph can never cycle back on itself.

Archiving/deleting a comment never cascades to its own replies — see
`archive`/`delete`'s own docstrings for the full "deleted/archived
parent handling" reasoning (existing replies are left exactly as they
are; only *new* replies to a dead parent are rejected, by
`CreateReplyService`, at creation time).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.events import (
    CommunityCommentArchived,
    CommunityCommentAttachmentAdded,
    CommunityCommentCreated,
    CommunityCommentDeleted,
    CommunityCommentPublished,
    CommunityCommentRestored,
    CommunityCommentRevisionCreated,
    CommunityCommentUpdated,
)
from app.modules.community_comments.domain.exceptions import (
    CommentAlreadyArchivedError,
    CommentAlreadyDeletedError,
    CommentAlreadyPublishedError,
    CommentCannotBeRestoredError,
    MaxCommentDepthExceededError,
)
from app.modules.community_comments.domain.value_objects import CommentBody, CommentId
from app.shared.domain.entity import AggregateRoot

MAX_COMMENT_DEPTH = 5
"""The deepest a reply may nest below its top-level comment (0 = the
comment itself). This task's own DOMAIN section leaves "maximum safe
nesting depth" to this module's own judgment ("according to domain
rules") — 5 comfortably exceeds the two-level "Comment -> Reply -> Reply"
example this task's own diagram shows, while staying shallow enough that
`get_thread`'s single bounded query (`depth <= max_depth`) never has to
scan an unreasonably deep chain."""


@dataclass(kw_only=True, eq=False)
class CommunityComment(AggregateRoot):
    target_type: CommentTargetType
    target_id: UUID
    community_id: UUID
    organization_id: UUID
    topic_id: UUID | None
    author_id: UUID
    body: CommentBody
    root_comment_id: UUID
    parent_comment_id: UUID | None = None
    depth: int = 0
    status: CommentStatus = CommentStatus.DRAFT
    is_anonymous: bool = False
    revision_number: int = 1
    published_at: datetime | None = None
    updated_by: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        target_type: CommentTargetType,
        target_id: UUID,
        community_id: UUID,
        organization_id: UUID,
        topic_id: UUID | None,
        author_id: UUID,
        body: CommentBody,
        is_anonymous: bool = False,
    ) -> "CommunityComment":
        """Creates a *top-level* comment: `parent_comment_id=None`,
        `depth=0`, `root_comment_id` equal to its own new id. Used by
        `CreateCommentService` only — see `create_reply` for the nested
        case, which this method never handles (no optional
        parent-context parameters here at all, so there is nothing for a
        caller to pass inconsistently)."""
        new_id = uuid4()
        comment = cls(
            id=new_id,
            target_type=target_type,
            target_id=target_id,
            community_id=community_id,
            organization_id=organization_id,
            topic_id=topic_id,
            author_id=author_id,
            body=body,
            parent_comment_id=None,
            root_comment_id=new_id,
            depth=0,
            is_anonymous=is_anonymous,
            updated_by=author_id,
        )
        comment.record_event(
            CommunityCommentCreated(
                comment_id=comment.id,
                target_type=target_type,
                target_id=target_id,
                author_id=author_id,
                parent_comment_id=None,
            )
        )
        return comment

    @classmethod
    def create_reply(
        cls,
        *,
        parent: "CommunityComment",
        author_id: UUID,
        body: CommentBody,
        is_anonymous: bool = False,
    ) -> "CommunityComment":
        """Creates a reply nested under `parent` (a top-level comment or
        another reply, at any depth) — `target_type`/`target_id`/
        `community_id`/`organization_id`/`topic_id`/`root_comment_id` are
        all copied directly from `parent`, never independently supplied
        or re-resolved, which is exactly what makes "no ambiguous or
        conflicting target ownership" (this task's own DOMAIN section)
        structurally impossible for a reply: it cannot disagree with its
        own parent's target because it never receives one of its own.

        Taking the parent as a full loaded entity (not just its scalar
        `id`) is what lets this method enforce `MAX_COMMENT_DEPTH` with
        a properly-typed, always-present `parent.id` — no
        `UUID | None` ambiguity the way a single unified `create()`
        accepting an optional parent id would have needed. The caller
        (`CreateReplyService`) is responsible for having already loaded
        `parent` via `CommunityCommentRepository.get_by_id` and confirmed
        it is `PUBLISHED` — this method only enforces the depth limit,
        not parent status (a domain entity has no repository access to
        second-guess a lookup its caller already performed)."""
        new_depth = parent.depth + 1
        if new_depth > MAX_COMMENT_DEPTH:
            raise MaxCommentDepthExceededError(parent.id, MAX_COMMENT_DEPTH)

        reply = cls(
            id=uuid4(),
            target_type=parent.target_type,
            target_id=parent.target_id,
            community_id=parent.community_id,
            organization_id=parent.organization_id,
            topic_id=parent.topic_id,
            author_id=author_id,
            body=body,
            parent_comment_id=parent.id,
            root_comment_id=parent.root_comment_id,
            depth=new_depth,
            is_anonymous=is_anonymous,
            updated_by=author_id,
        )
        reply.record_event(
            CommunityCommentCreated(
                comment_id=reply.id,
                target_type=parent.target_type,
                target_id=parent.target_id,
                author_id=author_id,
                parent_comment_id=parent.id,
            )
        )
        return reply

    def update_content(
        self, *, body: CommentBody | None = None, updated_by: UUID | None = None
    ) -> "CommunityCommentRevision | None":
        """Returns the archived snapshot of the *previous* body as a
        `CommunityCommentRevision`, or `None` if no revision was needed —
        a revision is only recorded when `body` is actually changing
        *and* the comment is currently `PUBLISHED` (this task's own
        REVISION HISTORY section: "Published comment edits must preserve
        immutable revision history" — a draft has never been publicly
        visible, so editing it before its first publish has nothing
        worth preserving). The caller (`UpdateCommentService`) is
        responsible for persisting the returned revision through
        `CommunityCommentRevisionRepository.add` in the same transaction
        — this method only decides *whether* one is needed and
        constructs it; it never touches a repository itself."""
        revision = None
        if (
            body is not None
            and str(body) != str(self.body)
            and self.status is CommentStatus.PUBLISHED
        ):
            revision = CommunityCommentRevision.create(
                comment_id=CommentId(self.id),
                revision_number=self.revision_number,
                previous_body=str(self.body),
                author_id=updated_by if updated_by is not None else self.author_id,
            )
            self.revision_number += 1

        if body is not None:
            self.body = body
        if updated_by is not None:
            self.updated_by = updated_by

        self.touch()
        self.record_event(CommunityCommentUpdated(comment_id=self.id))
        return revision

    def publish(self) -> None:
        if self.status is CommentStatus.PUBLISHED:
            raise CommentAlreadyPublishedError(self.id)
        self.status = CommentStatus.PUBLISHED
        self.published_at = datetime.now(UTC)
        self.touch()
        self.record_event(CommunityCommentPublished(comment_id=self.id))

    def archive(self) -> None:
        """Never cascades to this comment's own replies — a moderator
        archiving one message in a thread should not silently hide every
        reply beneath it. New replies to an archived parent are rejected
        by `CreateReplyService` at creation time instead — see this
        class's own module docstring."""
        if self.status is CommentStatus.ARCHIVED:
            raise CommentAlreadyArchivedError(self.id)
        self.status = CommentStatus.ARCHIVED
        self.touch()
        self.record_event(CommunityCommentArchived(comment_id=self.id))

    def restore(self) -> None:
        """The recovery action for `ARCHIVED`/`DELETED` comments —
        always lands on `DRAFT`, never straight back to `PUBLISHED`, so
        re-exposing restored content is always a separate, explicit
        `publish()` call rather than an implicit side effect of
        restoring — the same shape
        `CommunityAnswer.restore`'s own docstring establishes."""
        if self.status not in (CommentStatus.ARCHIVED, CommentStatus.DELETED):
            raise CommentCannotBeRestoredError(self.id)
        self.status = CommentStatus.DRAFT
        self.touch()
        self.record_event(CommunityCommentRestored(comment_id=self.id))

    def delete(self) -> None:
        """Business-visible soft delete via status transition — see
        `CommentStatus`'s own docstring. Never cascades to this
        comment's own replies — see `archive`'s own docstring for the
        identical reasoning."""
        if self.status is CommentStatus.DELETED:
            raise CommentAlreadyDeletedError(self.id)
        self.status = CommentStatus.DELETED
        self.touch()
        self.record_event(CommunityCommentDeleted(comment_id=self.id))


@dataclass(kw_only=True, eq=False)
class CommunityCommentRevision(AggregateRoot):
    """An immutable, append-only snapshot of a comment's *previous*
    content, taken automatically by `CommunityComment.update_content`
    whenever a published comment's body actually changes — see that
    method's own docstring. Never mutated or removed once created; see
    `CommunityCommentRevisionRepository`'s own docstring."""

    comment_id: CommentId
    revision_number: int
    previous_body: str
    author_id: UUID

    @classmethod
    def create(
        cls, *, comment_id: CommentId, revision_number: int, previous_body: str, author_id: UUID
    ) -> "CommunityCommentRevision":
        revision = cls(
            comment_id=comment_id,
            revision_number=revision_number,
            previous_body=previous_body,
            author_id=author_id,
        )
        revision.record_event(
            CommunityCommentRevisionCreated(
                revision_id=revision.id,
                comment_id=comment_id.value,
                revision_number=revision_number,
            )
        )
        return revision


@dataclass(kw_only=True, eq=False)
class CommunityCommentAttachment(AggregateRoot):
    comment_id: CommentId
    document_id: UUID

    @classmethod
    def create(cls, *, comment_id: CommentId, document_id: UUID) -> "CommunityCommentAttachment":
        attachment = cls(comment_id=comment_id, document_id=document_id)
        attachment.record_event(
            CommunityCommentAttachmentAdded(
                attachment_id=attachment.id, comment_id=comment_id.value, document_id=document_id
            )
        )
        return attachment
