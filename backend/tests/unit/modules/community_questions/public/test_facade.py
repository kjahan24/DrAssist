"""Unit tests for `QuestionFacade` — exercised through `QuestionQueryPort`
exactly as a future consumer module (Answers/Comments/Votes/AI Summary/...)
would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import QuestionVisibility
from app.modules.community_questions.domain.value_objects import QuestionTitle
from app.modules.community_questions.public.facade import QuestionFacade
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from tests.unit.modules.community_questions.application.fakes import FakeCommunityQuestionRepository


def _facade() -> tuple[QuestionFacade, FakeCommunityQuestionRepository]:
    questions = FakeCommunityQuestionRepository()
    facade = QuestionFacade(question_repository=questions)
    return facade, questions


def _make_question(**overrides: object) -> CommunityQuestion:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "primary_topic_id": uuid4(),
        "title": QuestionTitle("Title"),
        "body": "Body",
    }
    defaults.update(overrides)
    return CommunityQuestion.create(**defaults)  # type: ignore[arg-type]


class TestQuestionFacade:
    def test_is_a_question_query_port(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, QuestionQueryPort)

    async def test_question_exists_true_when_present(self) -> None:
        facade, questions = _facade()
        question = _make_question()
        await questions.add(question)

        assert await facade.question_exists(question.id) is True

    async def test_question_exists_false_when_absent(self) -> None:
        facade, _ = _facade()
        assert await facade.question_exists(uuid4()) is False

    async def test_get_question_summary_returns_a_summary_when_present(self) -> None:
        facade, questions = _facade()
        question = _make_question()
        await questions.add(question)

        summary = await facade.get_question_summary(question.id)

        assert summary is not None
        assert summary.question_id == question.id

    async def test_get_question_summary_returns_none_for_unknown_id(self) -> None:
        facade, _ = _facade()
        assert await facade.get_question_summary(uuid4()) is None

    async def test_get_question_summary_reflects_the_questions_current_title(self) -> None:
        facade, questions = _facade()
        question = _make_question(title=QuestionTitle("Original Title"))
        await questions.add(question)
        question.update_content(title=QuestionTitle("Renamed Title"))

        summary = await facade.get_question_summary(question.id)
        assert summary is not None
        assert summary.title == "Renamed Title"

    async def test_get_question_summary_does_not_enforce_visibility(self) -> None:
        """Module-to-module facade reads have no acting user, so
        `QuestionVisibility` (an end-user-facing rule) does not apply
        here — see `QuestionFacade`'s own docstring."""
        facade, questions = _facade()
        question = _make_question(visibility=QuestionVisibility.PRIVATE)
        await questions.add(question)

        summary = await facade.get_question_summary(question.id)
        assert summary is not None
