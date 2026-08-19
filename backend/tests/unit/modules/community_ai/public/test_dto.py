"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community_ai.application.dto import (
    AICommunityAnalysisSummaryDTO as ApplicationAICommunityAnalysisSummaryDTO,
)
from app.modules.community_ai.domain.enums import AIAnalysisStatus as DomainAIAnalysisStatus
from app.modules.community_ai.domain.enums import AIAnalysisType as DomainAIAnalysisType
from app.modules.community_ai.domain.enums import (
    CommunityContentTargetType as DomainCommunityContentTargetType,
)
from app.modules.community_ai.domain.enums import (
    MisinformationRiskLevel as DomainMisinformationRiskLevel,
)
from app.modules.community_ai.public.dto import (
    AIAnalysisStatus,
    AIAnalysisType,
    AICommunityAnalysisSummaryDTO,
    CommunityContentTargetType,
    MisinformationRiskLevel,
)


class TestPublicDtoReExports:
    def test_ai_community_analysis_summary_dto_is_the_application_type(self) -> None:
        assert AICommunityAnalysisSummaryDTO is ApplicationAICommunityAnalysisSummaryDTO

    def test_ai_analysis_status_is_the_domain_type(self) -> None:
        assert AIAnalysisStatus is DomainAIAnalysisStatus

    def test_ai_analysis_type_is_the_domain_type(self) -> None:
        assert AIAnalysisType is DomainAIAnalysisType

    def test_community_content_target_type_is_the_domain_type(self) -> None:
        assert CommunityContentTargetType is DomainCommunityContentTargetType

    def test_misinformation_risk_level_is_the_domain_type(self) -> None:
        assert MisinformationRiskLevel is DomainMisinformationRiskLevel
