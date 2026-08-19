"""The Community Comments module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.community_comments.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module — this file and `dto.py` are
the entire allowed surface today.

This is the read-only lookup port a future module (Votes, Notifications,
Moderation, AI Analysis — this task's own GOAL section anticipates
Comments as one of the discussion primitives those will eventually build
on) will need: resolve a comment id into a summary (or confirm one
exists) without depending on this module's own repositories/entities —
the same "query port for future consumer modules" shape
`app.modules.community_answers.public.interfaces.AnswerQueryPort`
already establishes for itself.

`get_thread_summaries` was added for Phase 5.10 (Community AI Features)'s
own "Long discussion threads" summarization target — the only way to
summarize an entire reply thread is to read every comment in it, which
`get_comment_summary`'s single-id lookup cannot do. It wraps this
module's own already-existing `CommunityCommentRepository.get_thread`
(bounded-depth, non-recursive, `(depth, created_at)`-ordered) — no new
domain capability, purely a narrow, additive read-only extension of this
port's existing surface.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_comments.public.dto import CommunityCommentSummaryDTO


class CommentQueryPort(ABC):
    @abstractmethod
    async def comment_exists(self, comment_id: UUID) -> bool: ...

    @abstractmethod
    async def get_comment_summary(self, comment_id: UUID) -> CommunityCommentSummaryDTO | None: ...

    @abstractmethod
    async def get_thread_summaries(self, root_comment_id: UUID) -> list[CommunityCommentSummaryDTO]:
        """Every comment in the thread rooted at `root_comment_id` (the
        root itself plus every descendant reply), ordered `(depth,
        created_at)` ascending. Empty list if `root_comment_id` doesn't
        exist."""
        ...
