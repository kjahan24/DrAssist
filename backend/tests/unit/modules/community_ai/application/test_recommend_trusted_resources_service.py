"""Unit tests for `RecommendTrustedResourcesService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community_ai.application.dto import RecommendTrustedResourcesInput
from app.modules.community_ai.application.services.recommend_trusted_resources_service import (
    RecommendTrustedResourcesService,
)
from app.modules.community_ai.domain.enums import AIAnalysisStatus, CommunityContentTargetType
from tests.unit.modules.community_ai.application.fakes import (
    FakeAICommunityAnalysisRepository,
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakeCommunityAIGeneratorPort,
    FakeCommunityQueryPort,
    FakeModerationQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeTrustedResourceCatalogPort,
    FakeUnitOfWork,
    make_post_summary,
    make_resource_recommendation,
)


def _seeded() -> (
    tuple[
        RecommendTrustedResourcesService,
        FakePostQueryPort,
        FakeCommunityAIGeneratorPort,
        FakeTrustedResourceCatalogPort,
    ]
):
    generator = FakeCommunityAIGeneratorPort()
    catalog = FakeTrustedResourceCatalogPort()
    posts = FakePostQueryPort()
    service = RecommendTrustedResourcesService(
        analysis_repository=FakeAICommunityAnalysisRepository(),
        generator=generator,
        catalog=catalog,
        post_query_port=posts,
        question_query_port=FakeQuestionQueryPort(),
        answer_query_port=FakeAnswerQueryPort(),
        comment_query_port=FakeCommentQueryPort(),
        community_query_port=FakeCommunityQueryPort(),
        moderation_query_port=FakeModerationQueryPort(),
        unit_of_work=FakeUnitOfWork(),
    )
    return service, posts, generator, catalog


class TestRecommendTrustedResources:
    async def test_returns_only_recommendations_the_generator_already_validated_against_the_catalog(
        self,
    ) -> None:
        service, posts, generator, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        generator.resource_results = (make_resource_recommendation(),)

        output = await service.execute(
            RecommendTrustedResourcesInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.status is AIAnalysisStatus.COMPLETED
        assert output.result is not None
        assert len(output.result["items"]) == 1

    async def test_passes_the_full_catalog_to_the_generator(self) -> None:
        service, posts, generator, catalog = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))

        await service.execute(
            RecommendTrustedResourcesInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert generator.calls == ["generate_resource_recommendations"]

    async def test_empty_catalog_result_still_completes_with_no_items(self) -> None:
        service, posts, generator, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        generator.resource_results = ()

        output = await service.execute(
            RecommendTrustedResourcesInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.status is AIAnalysisStatus.COMPLETED
        assert output.result == {"items": []}
