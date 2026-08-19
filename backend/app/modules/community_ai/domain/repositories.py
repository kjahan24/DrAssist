"""Repository interface (port) for the Community AI Features module.
Concrete implementation lives in `infrastructure/repositories.py`; the
application layer depends only on this ABC.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)


class AICommunityAnalysisRepository(ABC):
    @abstractmethod
    async def get_by_id(self, analysis_id: UUID) -> AICommunityAnalysis | None: ...

    @abstractmethod
    async def get_by_target(
        self,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        analysis_type: AIAnalysisType,
    ) -> AICommunityAnalysis | None:
        """The one row for this `(target_type, target_id, analysis_type)`
        triple, if any — the unique-constraint-backed key
        `RefreshAIAnalysis`/idempotent "already analyzed" lookups key
        off. `None` if this target has never had this analysis type
        requested."""
        ...

    @abstractmethod
    async def list_analyses(
        self,
        *,
        organization_id: UUID,
        target_type: CommunityContentTargetType | None = None,
        target_id: UUID | None = None,
        analysis_type: AIAnalysisType | None = None,
        status: AIAnalysisStatus | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[AICommunityAnalysis], str | None]: ...

    @abstractmethod
    async def add(self, analysis: AICommunityAnalysis) -> None: ...
