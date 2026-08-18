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
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_comments.public.dto import CommunityCommentSummaryDTO


class CommentQueryPort(ABC):
    @abstractmethod
    async def comment_exists(self, comment_id: UUID) -> bool: ...

    @abstractmethod
    async def get_comment_summary(self, comment_id: UUID) -> CommunityCommentSummaryDTO | None: ...
