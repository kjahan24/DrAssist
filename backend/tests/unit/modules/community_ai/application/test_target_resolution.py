"""Unit tests for `_target_resolution.resolve_analysis_target`."""

from uuid import uuid4

from app.modules.community_ai.application.services._target_resolution import (
    resolve_analysis_target,
)
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from tests.unit.modules.community_ai.application.fakes import (
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    make_answer_summary,
    make_comment_summary,
    make_post_summary,
    make_question_summary,
)


def _ports() -> (
    tuple[FakePostQueryPort, FakeQuestionQueryPort, FakeAnswerQueryPort, FakeCommentQueryPort]
):
    return (
        FakePostQueryPort(),
        FakeQuestionQueryPort(),
        FakeAnswerQueryPort(),
        FakeCommentQueryPort(),
    )


class TestResolveAnalysisTarget:
    async def test_resolves_a_post_with_its_real_author_id(self) -> None:
        posts, questions, answers, comments = _ports()
        author_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, is_anonymous=True, author_id=author_id))

        resolved = await resolve_analysis_target(
            CommunityContentTargetType.POST,
            post_id,
            post_query_port=posts,
            question_query_port=questions,
            answer_query_port=answers,
            comment_query_port=comments,
        )

        assert resolved is not None
        assert resolved.author_id == author_id
        assert resolved.title is not None

    async def test_resolves_a_question(self) -> None:
        posts, questions, answers, comments = _ports()
        question_id = uuid4()
        questions.add_question(make_question_summary(question_id=question_id))

        resolved = await resolve_analysis_target(
            CommunityContentTargetType.QUESTION,
            question_id,
            post_query_port=posts,
            question_query_port=questions,
            answer_query_port=answers,
            comment_query_port=comments,
        )

        assert resolved is not None
        assert resolved.text

    async def test_resolves_an_answer_with_no_title(self) -> None:
        posts, questions, answers, comments = _ports()
        answer_id = uuid4()
        answers.add_answer(make_answer_summary(answer_id=answer_id))

        resolved = await resolve_analysis_target(
            CommunityContentTargetType.ANSWER,
            answer_id,
            post_query_port=posts,
            question_query_port=questions,
            answer_query_port=answers,
            comment_query_port=comments,
        )

        assert resolved is not None
        assert resolved.title is None

    async def test_resolves_a_comment_thread_by_joining_all_published_replies(self) -> None:
        posts, questions, answers, comments = _ports()
        root_id = uuid4()
        root = make_comment_summary(comment_id=root_id, root_comment_id=root_id, body="Root text")
        reply = make_comment_summary(root_comment_id=root_id, body="Reply text")
        comments.add_comment(root)
        comments.add_comment(reply)

        resolved = await resolve_analysis_target(
            CommunityContentTargetType.COMMENT,
            root_id,
            post_query_port=posts,
            question_query_port=questions,
            answer_query_port=answers,
            comment_query_port=comments,
        )

        assert resolved is not None
        assert "Root text" in resolved.text
        assert "Reply text" in resolved.text
        assert resolved.author_id is None
        assert resolved.visibility_value is None

    async def test_comment_thread_excludes_non_published_replies(self) -> None:
        from app.modules.community_comments.public.dto import CommentStatus

        posts, questions, answers, comments = _ports()
        root_id = uuid4()
        root = make_comment_summary(comment_id=root_id, root_comment_id=root_id, body="Root text")
        deleted_reply = make_comment_summary(
            root_comment_id=root_id, body="Deleted reply", status=CommentStatus.DELETED
        )
        comments.add_comment(root)
        comments.add_comment(deleted_reply)

        resolved = await resolve_analysis_target(
            CommunityContentTargetType.COMMENT,
            root_id,
            post_query_port=posts,
            question_query_port=questions,
            answer_query_port=answers,
            comment_query_port=comments,
        )

        assert resolved is not None
        assert "Deleted reply" not in resolved.text

    async def test_returns_none_for_an_unknown_post(self) -> None:
        posts, questions, answers, comments = _ports()

        resolved = await resolve_analysis_target(
            CommunityContentTargetType.POST,
            uuid4(),
            post_query_port=posts,
            question_query_port=questions,
            answer_query_port=answers,
            comment_query_port=comments,
        )

        assert resolved is None
