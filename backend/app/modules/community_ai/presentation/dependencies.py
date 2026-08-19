"""Module-specific FastAPI dependency providers.

Constructs the request-scoped repository, Unit of Work, and services for
this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession`. `get_*_query_port` providers each
call the respective peer module's own `build_*_facade(session)`
composition-root factory — never construct a facade directly, the same
rule every prior module's own `presentation/dependencies.py` establishes.

`get_community_ai_generator`/`get_similar_discussion_search`/
`get_trusted_resource_catalog` are process-lifetime singletons from
`app.modules.community_ai.container` (no session dependency) — injected
here alongside the per-request pieces, the same split that module's own
docstring explains.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.community.container import build_community_facade
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_ai.application.ports import (
    CommunityAIGeneratorPort,
    SimilarDiscussionSearchPort,
    TrustedResourceCatalogPort,
)
from app.modules.community_ai.application.services.analysis_query_service import (
    GetAIAnalysisService,
    ListAIAnalysesService,
)
from app.modules.community_ai.application.services.analyze_misinformation_service import (
    AnalyzeMisinformationService,
)
from app.modules.community_ai.application.services.find_similar_discussions_service import (
    FindSimilarDiscussionsService,
)
from app.modules.community_ai.application.services.generate_discussion_summary_service import (
    GenerateDiscussionSummaryService,
)
from app.modules.community_ai.application.services.recommend_trusted_resources_service import (
    RecommendTrustedResourcesService,
)
from app.modules.community_ai.application.services.refresh_ai_analysis_service import (
    RefreshAIAnalysisService,
)
from app.modules.community_ai.container import (
    get_community_ai_generator,
    get_similar_discussion_search,
    get_trusted_resource_catalog,
)
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_ai.infrastructure.repositories import (
    SqlAlchemyAICommunityAnalysisRepository,
)
from app.modules.community_answers.container import build_answer_facade
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.container import build_comment_facade
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.container import build_moderation_facade
from app.modules.community_moderation.public.interfaces import ModerationQueryPort
from app.modules.community_posts.container import build_post_facade
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.container import build_question_facade
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_analysis_repository(session: DbSession) -> AICommunityAnalysisRepository:
    return SqlAlchemyAICommunityAnalysisRepository(session)


def get_post_query_port(session: DbSession) -> PostQueryPort:
    return build_post_facade(session)


def get_question_query_port(session: DbSession) -> QuestionQueryPort:
    return build_question_facade(session)


def get_answer_query_port(session: DbSession) -> AnswerQueryPort:
    return build_answer_facade(session)


def get_comment_query_port(session: DbSession) -> CommentQueryPort:
    return build_comment_facade(session)


def get_community_query_port(session: DbSession) -> CommunityQueryPort:
    return build_community_facade(session)


def get_moderation_query_port(session: DbSession) -> ModerationQueryPort:
    return build_moderation_facade(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


AnalysisRepo = Annotated[AICommunityAnalysisRepository, Depends(get_analysis_repository)]
PostPort = Annotated[PostQueryPort, Depends(get_post_query_port)]
QuestionPort = Annotated[QuestionQueryPort, Depends(get_question_query_port)]
AnswerPort = Annotated[AnswerQueryPort, Depends(get_answer_query_port)]
CommentPort = Annotated[CommentQueryPort, Depends(get_comment_query_port)]
CommunityPort = Annotated[CommunityQueryPort, Depends(get_community_query_port)]
ModerationPort = Annotated[ModerationQueryPort, Depends(get_moderation_query_port)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
Generator = Annotated[CommunityAIGeneratorPort, Depends(get_community_ai_generator)]
SearchPort = Annotated[SimilarDiscussionSearchPort, Depends(get_similar_discussion_search)]
Catalog = Annotated[TrustedResourceCatalogPort, Depends(get_trusted_resource_catalog)]


def get_generate_discussion_summary_service(
    analysis_repository: AnalysisRepo,
    generator: Generator,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    moderation_port: ModerationPort,
    unit_of_work: Uow,
) -> GenerateDiscussionSummaryService:
    return GenerateDiscussionSummaryService(
        analysis_repository=analysis_repository,
        generator=generator,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        moderation_query_port=moderation_port,
        unit_of_work=unit_of_work,
    )


def get_find_similar_discussions_service(
    analysis_repository: AnalysisRepo,
    search_port: SearchPort,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    moderation_port: ModerationPort,
    unit_of_work: Uow,
) -> FindSimilarDiscussionsService:
    return FindSimilarDiscussionsService(
        analysis_repository=analysis_repository,
        search_port=search_port,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        moderation_query_port=moderation_port,
        unit_of_work=unit_of_work,
    )


def get_recommend_trusted_resources_service(
    analysis_repository: AnalysisRepo,
    generator: Generator,
    catalog: Catalog,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    moderation_port: ModerationPort,
    unit_of_work: Uow,
) -> RecommendTrustedResourcesService:
    return RecommendTrustedResourcesService(
        analysis_repository=analysis_repository,
        generator=generator,
        catalog=catalog,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        moderation_query_port=moderation_port,
        unit_of_work=unit_of_work,
    )


def get_analyze_misinformation_service(
    analysis_repository: AnalysisRepo,
    generator: Generator,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    moderation_port: ModerationPort,
    unit_of_work: Uow,
) -> AnalyzeMisinformationService:
    return AnalyzeMisinformationService(
        analysis_repository=analysis_repository,
        generator=generator,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        moderation_query_port=moderation_port,
        unit_of_work=unit_of_work,
    )


def get_refresh_ai_analysis_service(
    analysis_repository: AnalysisRepo,
    generator: Generator,
    search_port: SearchPort,
    catalog: Catalog,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    moderation_port: ModerationPort,
    unit_of_work: Uow,
) -> RefreshAIAnalysisService:
    return RefreshAIAnalysisService(
        analysis_repository=analysis_repository,
        generator=generator,
        search_port=search_port,
        catalog=catalog,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        moderation_query_port=moderation_port,
        unit_of_work=unit_of_work,
    )


def get_get_ai_analysis_service(analysis_repository: AnalysisRepo) -> GetAIAnalysisService:
    return GetAIAnalysisService(analysis_repository=analysis_repository)


def get_list_ai_analyses_service(analysis_repository: AnalysisRepo) -> ListAIAnalysesService:
    return ListAIAnalysesService(analysis_repository=analysis_repository)


GenerateSummaryUseCase = Annotated[
    GenerateDiscussionSummaryService, Depends(get_generate_discussion_summary_service)
]
FindSimilarDiscussionsUseCase = Annotated[
    FindSimilarDiscussionsService, Depends(get_find_similar_discussions_service)
]
RecommendTrustedResourcesUseCase = Annotated[
    RecommendTrustedResourcesService, Depends(get_recommend_trusted_resources_service)
]
AnalyzeMisinformationUseCase = Annotated[
    AnalyzeMisinformationService, Depends(get_analyze_misinformation_service)
]
RefreshAIAnalysisUseCase = Annotated[
    RefreshAIAnalysisService, Depends(get_refresh_ai_analysis_service)
]
GetAIAnalysisQS = Annotated[GetAIAnalysisService, Depends(get_get_ai_analysis_service)]
ListAIAnalysesQS = Annotated[ListAIAnalysesService, Depends(get_list_ai_analyses_service)]
