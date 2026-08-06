"""The Community Posts module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.community_posts.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module — this file and `dto.py` are
the entire allowed surface today.

This is the read-only lookup port this task's own DO-NOT-IMPLEMENT list
anticipates: Questions/Answers/Comments/AI Summary/AI Similar
Discussions (all explicitly future modules) will need to resolve a post
id into a summary (or confirm one exists) without depending on this
module's own repositories/entities — the same "query port for future
consumer modules" shape `CommunityQueryPort`/`TopicQueryPort`/
`DocumentQueryPort` already establish for themselves.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_posts.public.dto import CommunityPostSummaryDTO


class PostQueryPort(ABC):
    @abstractmethod
    async def post_exists(self, post_id: UUID) -> bool: ...

    @abstractmethod
    async def get_post_summary(self, post_id: UUID) -> CommunityPostSummaryDTO | None: ...
