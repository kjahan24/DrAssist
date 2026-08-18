"""Unit tests for `AnswerFacade` — exercised through `AnswerQueryPort`
exactly as a future consumer module (Votes/Comments/Reputation/AI
Analysis/...) would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerVisibility
from app.modules.community_answers.domain.value_objects import AnswerBody
from app.modules.community_answers.public.facade import AnswerFacade
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from tests.unit.modules.community_answers.application.fakes import FakeCommunityAnswerRepository


def _facade() -> tuple[AnswerFacade, FakeCommunityAnswerRepository]:
    answers = FakeCommunityAnswerRepository()
    facade = AnswerFacade(answer_repository=answers)
    return facade, answers


def _make_answer(**overrides: object) -> CommunityAnswer:
    defaults: dict[str, object] = {
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
        "author_id": uuid4(),
        "body": AnswerBody("Body."),
    }
    defaults.update(overrides)
    return CommunityAnswer.create(**defaults)  # type: ignore[arg-type]


class TestAnswerFacade:
    def test_is_an_answer_query_port(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, AnswerQueryPort)

    async def test_answer_exists_true_when_present(self) -> None:
        facade, answers = _facade()
        answer = _make_answer()
        await answers.add(answer)

        assert await facade.answer_exists(answer.id) is True

    async def test_answer_exists_false_when_absent(self) -> None:
        facade, _ = _facade()
        assert await facade.answer_exists(uuid4()) is False

    async def test_get_answer_summary_returns_a_summary_when_present(self) -> None:
        facade, answers = _facade()
        answer = _make_answer()
        await answers.add(answer)

        summary = await facade.get_answer_summary(answer.id)

        assert summary is not None
        assert summary.answer_id == answer.id

    async def test_get_answer_summary_returns_none_for_unknown_id(self) -> None:
        facade, _ = _facade()
        assert await facade.get_answer_summary(uuid4()) is None

    async def test_get_answer_summary_reflects_the_answers_current_body(self) -> None:
        facade, answers = _facade()
        answer = _make_answer(body=AnswerBody("Original body."))
        await answers.add(answer)
        answer.update_content(body=AnswerBody("Edited body."))

        summary = await facade.get_answer_summary(answer.id)
        assert summary is not None
        assert summary.body == "Edited body."

    async def test_get_answer_summary_masks_the_author_id_for_an_anonymous_answer(self) -> None:
        """Module-to-module facade reads reuse `answer_to_summary`
        unchanged, so anonymous masking applies here too — see that
        mapper's own docstring."""
        facade, answers = _facade()
        answer = _make_answer(is_anonymous=True)
        await answers.add(answer)

        summary = await facade.get_answer_summary(answer.id)
        assert summary is not None
        assert summary.author_id is None

    async def test_get_answer_summary_does_not_enforce_visibility(self) -> None:
        """Module-to-module facade reads have no acting user, so
        `AnswerVisibility` (an end-user-facing rule) does not apply here
        — see `AnswerFacade`'s own docstring."""
        facade, answers = _facade()
        answer = _make_answer(visibility=AnswerVisibility.PRIVATE)
        await answers.add(answer)

        summary = await facade.get_answer_summary(answer.id)
        assert summary is not None
