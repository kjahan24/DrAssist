"""Unit tests for `FindSimilarDiscussionsService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community_ai.application.dto import FindSimilarDiscussionsInput
from app.modules.community_ai.application.services.find_similar_discussions_service import (
    FindSimilarDiscussionsService,
)
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_ai.domain.value_objects import SimilarDiscussion
from tests.unit.modules.community_ai.application.fakes import (
    FakeAICommunityAnalysisRepository,
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakeCommunityQueryPort,
    FakeModerationQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeSimilarDiscussionSearchPort,
    FakeUnitOfWork,
    make_post_summary,
)


def _seeded() -> (
    tuple[
        FindSimilarDiscussionsService,
        FakePostQueryPort,
        FakeSimilarDiscussionSearchPort,
        FakeModerationQueryPort,
    ]
):
    search = FakeSimilarDiscussionSearchPort()
    posts = FakePostQueryPort()
    moderation = FakeModerationQueryPort()
    service = FindSimilarDiscussionsService(
        analysis_repository=FakeAICommunityAnalysisRepository(),
        search_port=search,
        post_query_port=posts,
        question_query_port=FakeQuestionQueryPort(),
        answer_query_port=FakeAnswerQueryPort(),
        comment_query_port=FakeCommentQueryPort(),
        community_query_port=FakeCommunityQueryPort(),
        moderation_query_port=moderation,
        unit_of_work=FakeUnitOfWork(),
    )
    return service, posts, search, moderation


class TestFindSimilarDiscussions:
    async def test_indexes_the_source_before_searching(self) -> None:
        service, posts, search, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))

        await service.execute(
            FindSimilarDiscussionsInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert search.indexed == [(CommunityContentTargetType.POST, post_id)]

    async def test_returns_empty_results_when_the_vector_store_has_no_other_candidates(
        self,
    ) -> None:
        service, posts, search, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        search.candidates = ()

        output = await service.execute(
            FindSimilarDiscussionsInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.items == []

    async def test_drops_a_candidate_that_belongs_to_a_different_organization(self) -> None:
        service, posts, search, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        other_org_post_id = uuid4()
        posts.add_post(make_post_summary(post_id=other_org_post_id, organization_id=uuid4()))
        search.candidates = (
            SimilarDiscussion(
                target_type=CommunityContentTargetType.POST,
                target_id=other_org_post_id,
                similarity_score=0.9,
            ),
        )

        output = await service.execute(
            FindSimilarDiscussionsInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.items == []

    async def test_drops_a_moderated_candidate(self) -> None:
        from app.modules.community_moderation.public.dto import ModerationTargetType

        service, posts, search, moderation = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        candidate_id = uuid4()
        posts.add_post(make_post_summary(post_id=candidate_id, organization_id=org_id))
        moderation.set_content_status(ModerationTargetType.POST, candidate_id, "removed")
        search.candidates = (
            SimilarDiscussion(
                target_type=CommunityContentTargetType.POST,
                target_id=candidate_id,
                similarity_score=0.9,
            ),
        )

        output = await service.execute(
            FindSimilarDiscussionsInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.items == []

    async def test_pagination_returns_disjoint_pages_across_two_candidates(self) -> None:
        service, posts, search, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        candidate_one, candidate_two = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=candidate_one, organization_id=org_id))
        posts.add_post(make_post_summary(post_id=candidate_two, organization_id=org_id))
        search.candidates = (
            SimilarDiscussion(
                target_type=CommunityContentTargetType.POST,
                target_id=candidate_one,
                similarity_score=0.9,
            ),
            SimilarDiscussion(
                target_type=CommunityContentTargetType.POST,
                target_id=candidate_two,
                similarity_score=0.75,
            ),
        )

        first_page = await service.execute(
            FindSimilarDiscussionsInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
                limit=1,
            )
        )
        assert [item.target_id for item in first_page.items] == [candidate_one]
        assert first_page.next_cursor is not None

        second_page = await service.execute(
            FindSimilarDiscussionsInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
                cursor=first_page.next_cursor,
                limit=1,
            )
        )
        assert [item.target_id for item in second_page.items] == [candidate_two]
        assert second_page.analysis_id == first_page.analysis_id
