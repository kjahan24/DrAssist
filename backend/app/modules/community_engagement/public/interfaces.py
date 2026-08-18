"""The Community Engagement module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.community_engagement.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module — this file and `dto.py`
are the entire allowed surface today.

`get_vote_counts` is the one read this port exposes today — a future
"trending content" ranking module, a Reputation module, or a
notification digest are the kinds of future consumers this task's own
GOAL section anticipates ("the production-grade engagement foundation
for" every other community module); each would need to resolve a
target's vote counts without depending on this module's own repositories
— the same "query port for future consumer modules" shape
`app.modules.community_comments.public.interfaces.CommentQueryPort`
already establishes for itself. Save/follow existence checks are
deliberately not exposed here yet — nothing in this codebase needs them
today, and adding an unused port method would be speculative surface
this task's own conventions elsewhere avoid.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_engagement.public.dto import EngagementTargetType, VoteCountsDTO


class EngagementQueryPort(ABC):
    @abstractmethod
    async def get_vote_counts(
        self, target_type: EngagementTargetType, target_id: UUID
    ) -> VoteCountsDTO: ...
