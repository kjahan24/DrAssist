"""Application services for the Community AI Features module — 7 named
use cases from this task's own APPLICATION section, across 6 files:

`GenerateDiscussionSummary` (`generate_discussion_summary_service.py`),
`FindSimilarDiscussions` (`find_similar_discussions_service.py`),
`RecommendTrustedResources` (`recommend_trusted_resources_service.py`),
`AnalyzeMisinformation` (`analyze_misinformation_service.py`),
`RefreshAIAnalysis` (`refresh_ai_analysis_service.py`),
`GetAIAnalysis`+`ListAIAnalyses` (one file, `analysis_query_service.py`).

Shared helpers (not use cases themselves): `_target_resolution.py`
(resolves a `(target_type, target_id)` pair across
`community_posts`/`community_questions`/`community_answers`/
`community_comments`), `_authorization.py` (tenant/visibility/moderation
enforcement), `_analysis_lifecycle.py` (idempotent get-or-start-analysis),
`_result_serialization.py` (domain value object <-> JSONB dict), and
`_summary_mappers.py` (`AICommunityAnalysis` -> `AICommunityAnalysisSummaryDTO`).
"""
