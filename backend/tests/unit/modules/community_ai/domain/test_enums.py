"""Sanity tests confirming every enum member the task's own AI
FEATURES/DOMAIN sections name is actually present."""

from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
    MisinformationRiskLevel,
    ResourceType,
)


class TestCommunityContentTargetType:
    def test_has_every_content_target(self) -> None:
        assert {member.value for member in CommunityContentTargetType} == {
            "post",
            "question",
            "answer",
            "comment",
        }


class TestAIAnalysisType:
    def test_has_every_named_analysis_type(self) -> None:
        assert {member.value for member in AIAnalysisType} == {
            "summary",
            "similar_discussions",
            "resource_recommendation",
            "misinformation",
        }


class TestAIAnalysisStatus:
    def test_has_every_lifecycle_state(self) -> None:
        assert {member.value for member in AIAnalysisStatus} == {
            "pending",
            "processing",
            "completed",
            "failed",
        }


class TestMisinformationRiskLevel:
    def test_has_every_named_risk_level(self) -> None:
        assert {member.value for member in MisinformationRiskLevel} == {
            "low",
            "medium",
            "high",
            "critical",
        }


class TestResourceType:
    def test_has_a_reasonable_set_of_resource_types(self) -> None:
        assert {member.value for member in ResourceType} == {
            "article",
            "guideline",
            "research_paper",
            "website",
            "organization",
            "other",
        }
