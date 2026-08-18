"""Unit tests for `CreateCommentService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_answers.public.dto import AnswerStatus, AnswerVisibility
from app.modules.community_comments.application.dto import CreateCommentInput
from app.modules.community_comments.application.services.create_comment_service import (
    CreateCommentService,
)
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.events import CommunityCommentCreated
from app.modules.community_comments.domain.exceptions import (
    CommentMembershipRequiredError,
    TargetNotAcceptingCommentsError,
    TargetNotFoundForCommentError,
    TargetNotViewableForCommentError,
)
from app.modules.community_posts.public.dto import PostStatus, PostVisibility
from app.modules.community_questions.public.dto import QuestionStatus, QuestionVisibility
from tests.unit.modules.community_comments.application.fakes import (
    FakeAnswerQueryPort,
    FakeCommunityCommentRepository,
    FakeCommunityQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeUnitOfWork,
    make_answer_summary,
    make_member_summary,
    make_post_summary,
    make_question_summary,
)


def _seeded() -> (
    tuple[
        CreateCommentService,
        FakeCommunityCommentRepository,
        FakeCommunityQueryPort,
        FakePostQueryPort,
        FakeQuestionQueryPort,
        FakeAnswerQueryPort,
        FakeUnitOfWork,
    ]
):
    comments = FakeCommunityCommentRepository()
    communities = FakeCommunityQueryPort()
    posts = FakePostQueryPort()
    questions = FakeQuestionQueryPort()
    answers = FakeAnswerQueryPort()
    uow = FakeUnitOfWork()
    service = CreateCommentService(
        comment_repository=comments,
        community_query_port=communities,
        post_query_port=posts,
        question_query_port=questions,
        answer_query_port=answers,
        unit_of_work=uow,
    )
    return service, comments, communities, posts, questions, answers, uow


def _seed_membership(
    communities: FakeCommunityQueryPort, *, community_id: object, user_id: object
) -> None:
    communities.add_membership(make_member_summary(community_id=community_id, user_id=user_id))


class TestCreateCommentOnPost:
    async def test_creates_a_comment(self) -> None:
        service, comments, communities, posts, _, _, _ = _seeded()
        community_id, author_id, post_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(make_post_summary(post_id=post_id, community_id=community_id))

        output = await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.POST,
                target_id=post_id,
                author_id=author_id,
                body="A comment body.",
            )
        )
        stored = await comments.get_by_id(output.comment_id)
        assert stored is not None
        assert str(stored.body) == "A comment body."
        assert stored.target_type is CommentTargetType.POST
        assert stored.target_id == post_id

    async def test_denormalizes_community_and_organization_from_the_post(self) -> None:
        service, comments, communities, posts, _, _, _ = _seeded()
        community_id, author_id, post_id, organization_id = uuid4(), uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(
            make_post_summary(
                post_id=post_id, community_id=community_id, organization_id=organization_id
            )
        )

        output = await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.POST,
                target_id=post_id,
                author_id=author_id,
                body="Body.",
            )
        )
        stored = await comments.get_by_id(output.comment_id)
        assert stored is not None
        assert stored.community_id == community_id
        assert stored.organization_id == organization_id

    async def test_post_target_has_no_topic(self) -> None:
        service, comments, communities, posts, _, _, _ = _seeded()
        community_id, author_id, post_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(make_post_summary(post_id=post_id, community_id=community_id))

        output = await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.POST,
                target_id=post_id,
                author_id=author_id,
                body="Body.",
            )
        )
        stored = await comments.get_by_id(output.comment_id)
        assert stored is not None
        assert stored.topic_id is None

    async def test_draft_post_rejects_new_comments(self) -> None:
        service, _, communities, posts, _, _, _ = _seeded()
        community_id, author_id, post_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, status=PostStatus.DRAFT)
        )

        with pytest.raises(TargetNotAcceptingCommentsError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.POST,
                    target_id=post_id,
                    author_id=author_id,
                    body="Body.",
                )
            )

    async def test_unknown_post_raises(self) -> None:
        service, _, communities, _, _, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        with pytest.raises(TargetNotFoundForCommentError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.POST,
                    target_id=uuid4(),
                    author_id=author_id,
                    body="Body.",
                )
            )

    async def test_private_post_not_authored_by_caller_rejects_the_comment(self) -> None:
        service, _, communities, posts, _, _, _ = _seeded()
        community_id, author_id, post_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(
            make_post_summary(
                post_id=post_id,
                community_id=community_id,
                visibility=PostVisibility.PRIVATE,
                author_id=uuid4(),
            )
        )

        with pytest.raises(TargetNotViewableForCommentError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.POST,
                    target_id=post_id,
                    author_id=author_id,
                    body="Body.",
                )
            )

    async def test_non_member_raises(self) -> None:
        service, _, _, posts, _, _, _ = _seeded()
        community_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, community_id=community_id))

        with pytest.raises(CommentMembershipRequiredError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.POST,
                    target_id=post_id,
                    author_id=uuid4(),
                    body="Body.",
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, communities, posts, _, _, uow = _seeded()
        community_id, author_id, post_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(make_post_summary(post_id=post_id, community_id=community_id))

        await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.POST,
                target_id=post_id,
                author_id=author_id,
                body="Body.",
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_comment_created_event(self) -> None:
        service, _, communities, posts, _, _, uow = _seeded()
        community_id, author_id, post_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(make_post_summary(post_id=post_id, community_id=community_id))

        await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.POST,
                target_id=post_id,
                author_id=author_id,
                body="Body.",
            )
        )
        assert any(isinstance(e, CommunityCommentCreated) for e in uow.published_events)

    async def test_new_comment_defaults_to_draft_status(self) -> None:
        service, _, communities, posts, _, _, _ = _seeded()
        community_id, author_id, post_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        posts.add_post(make_post_summary(post_id=post_id, community_id=community_id))

        output = await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.POST,
                target_id=post_id,
                author_id=author_id,
                body="Body.",
            )
        )
        assert output.status is CommentStatus.DRAFT


class TestCreateCommentOnQuestion:
    async def test_denormalizes_topic_from_the_question(self) -> None:
        service, comments, communities, _, questions, _, _ = _seeded()
        community_id, author_id, question_id, topic_id = uuid4(), uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, primary_topic_id=topic_id
            )
        )

        output = await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.QUESTION,
                target_id=question_id,
                author_id=author_id,
                body="Body.",
            )
        )
        stored = await comments.get_by_id(output.comment_id)
        assert stored is not None
        assert stored.topic_id == topic_id

    async def test_draft_question_rejects_new_comments(self) -> None:
        service, _, communities, _, questions, _, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, status=QuestionStatus.DRAFT
            )
        )

        with pytest.raises(TargetNotAcceptingCommentsError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.QUESTION,
                    target_id=question_id,
                    author_id=author_id,
                    body="Body.",
                )
            )

    async def test_members_only_question_requires_active_membership(self) -> None:
        service, _, communities, _, questions, _, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        questions.add_question(
            make_question_summary(
                question_id=question_id,
                community_id=community_id,
                visibility=QuestionVisibility.MEMBERS_ONLY,
            )
        )

        with pytest.raises(CommentMembershipRequiredError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.QUESTION,
                    target_id=question_id,
                    author_id=author_id,
                    body="Body.",
                )
            )


class TestCreateCommentOnAnswer:
    async def test_denormalizes_topic_from_the_answer(self) -> None:
        service, comments, communities, _, _, answers, _ = _seeded()
        community_id, author_id, answer_id, topic_id = uuid4(), uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        answers.add_answer(
            make_answer_summary(answer_id=answer_id, community_id=community_id, topic_id=topic_id)
        )

        output = await service.execute(
            CreateCommentInput(
                target_type=CommentTargetType.ANSWER,
                target_id=answer_id,
                author_id=author_id,
                body="Body.",
            )
        )
        stored = await comments.get_by_id(output.comment_id)
        assert stored is not None
        assert stored.topic_id == topic_id

    async def test_draft_answer_rejects_new_comments(self) -> None:
        service, _, communities, _, _, answers, _ = _seeded()
        community_id, author_id, answer_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        answers.add_answer(
            make_answer_summary(
                answer_id=answer_id, community_id=community_id, status=AnswerStatus.DRAFT
            )
        )

        with pytest.raises(TargetNotAcceptingCommentsError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.ANSWER,
                    target_id=answer_id,
                    author_id=author_id,
                    body="Body.",
                )
            )

    async def test_anonymous_answer_author_still_treated_as_no_confirmed_author(self) -> None:
        """`CommunityAnswerSummaryDTO.author_id` is masked to `None` for
        an anonymous answer, even for this module-to-module read — a
        `PRIVATE` anonymous answer's own true author can no longer
        self-identify through this path; see `ResolvedTarget`'s own
        docstring."""
        service, _, communities, _, _, answers, _ = _seeded()
        community_id, author_id, answer_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        answers.add_answer(
            make_answer_summary(
                answer_id=answer_id,
                community_id=community_id,
                visibility=AnswerVisibility.PRIVATE,
                is_anonymous=True,
                author_id=None,
            )
        )

        with pytest.raises(TargetNotViewableForCommentError):
            await service.execute(
                CreateCommentInput(
                    target_type=CommentTargetType.ANSWER,
                    target_id=answer_id,
                    author_id=author_id,
                    body="Body.",
                )
            )
