"""The Community AI Features module's public port — the only contract
another module may depend on.

Never import from `app.modules.community_ai.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module — this file and `dto.py` are
the entire allowed surface today.

Deliberately minimal — one read-only method, mirroring
`app.modules.community_moderation.public.interfaces.ModerationQueryPort`'s
own "expose only what a real, anticipated caller needs today" precedent:
`get_latest_completed_analysis` is the seam a future dashboard/moderation
integration would use to show an already-computed AI analysis (e.g. a
misinformation risk badge) without re-running one — it returns `None`
rather than triggering generation, since triggering AI generation is a
write-adjacent, potentially-costly operation that belongs only behind
this module's own `GenerateDiscussionSummary`/`AnalyzeMisinformation`/etc.
use cases, never behind a peer module's read.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_ai.public.dto import (
    AIAnalysisType,
    AICommunityAnalysisSummaryDTO,
    CommunityContentTargetType,
)


class CommunityAIQueryPort(ABC):
    @abstractmethod
    async def get_latest_completed_analysis(
        self,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        analysis_type: AIAnalysisType,
        *,
        organization_id: UUID,
    ) -> AICommunityAnalysisSummaryDTO | None:
        """The `COMPLETED` row for this `(target_type, target_id,
        analysis_type)`, if one exists and belongs to `organization_id` —
        `None` otherwise (including "belongs to a different tenant" or
        "exists but is still PENDING/PROCESSING/FAILED"), the same
        anti-enumeration posture `_target_resolution.py`'s own docstring
        establishes for the rest of this module."""
        ...
