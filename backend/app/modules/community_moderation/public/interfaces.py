"""The Community Moderation module's public port — the only contract
another module may depend on.

Never import from `app.modules.community_moderation.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module — this file and `dto.py`
are the entire allowed surface today.

Deliberately minimal — three read-only methods, mirroring
`app.modules.community_engagement.public.interfaces.EngagementQueryPort`'s
own "expose only what a real, anticipated caller needs today" precedent:

- `get_content_moderation_status` is the seam a future content-module
  integration would use to filter `REMOVED`/`RESTRICTED` items out of its
  own feed/search results — see `entities.py`'s own module docstring for
  why that wiring is out of scope for this task itself.
- `get_user_moderation_status` is the seam a future authorization check
  (e.g. "block a suspended user from posting") would use.
- `get_verification_status` is the seam a future "Verified Doctor" badge
  display (in a post/answer/question summary) would use.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_moderation.domain.enums import ModerationTargetType
from app.modules.community_moderation.domain.value_objects import UserModerationStatus
from app.modules.community_moderation.public.dto import VerificationSummaryDTO


class ModerationQueryPort(ABC):
    @abstractmethod
    async def get_content_moderation_status(
        self, target_type: ModerationTargetType, target_id: UUID
    ) -> str:
        """One of `app.modules.community_moderation.domain.enums
        .ContentModerationStatus`'s values (`"active"` if the target has
        never had a moderation action recorded against it)."""
        ...

    @abstractmethod
    async def get_user_moderation_status(
        self, user_id: UUID, *, community_id: UUID | None = None
    ) -> UserModerationStatus: ...

    @abstractmethod
    async def get_verification_status(self, doctor_id: UUID) -> VerificationSummaryDTO | None: ...
