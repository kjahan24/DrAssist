"""Integration tests for `SqlAlchemyCommunityAnswerRevisionRepository`
against a real PostgreSQL instance — round-trip persistence, ordering by
`revision_number` descending, and confirming there is genuinely no
update/remove path through this repository (see its own docstring:
revision history is immutable, full stop).

`community_answer_revisions.answer_id`/`.author_id` are real foreign
keys (`-> community_answers.id`/`-> users.id`), so every revision here
is created against an actual persisted `CommunityAnswer` and `User` —
see `_helpers.persist_org_user_community_question`.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_answers._helpers import (
    persist_org_user_community_question,
    persist_user,
)

from app.modules.community_answers.domain.entities import CommunityAnswer, CommunityAnswerRevision
from app.modules.community_answers.domain.repositories import CommunityAnswerRevisionRepository
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerId
from app.modules.community_answers.infrastructure.repositories import (
    SqlAlchemyCommunityAnswerRepository,
    SqlAlchemyCommunityAnswerRevisionRepository,
)


async def _persist_answer(db_session: AsyncSession) -> tuple[CommunityAnswer, object]:
    organization, user, community, topic, question = await persist_org_user_community_question(
        db_session
    )
    answers = SqlAlchemyCommunityAnswerRepository(db_session)
    answer = CommunityAnswer.create(
        question_id=question.id,
        community_id=community.id,
        organization_id=organization.id,
        topic_id=topic.id,
        author_id=user.id,
        body=AnswerBody("Original body."),
    )
    await answers.add(answer)
    await db_session.commit()
    return answer, organization.id


class TestCommunityAnswerRevisionRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        answer, organization_id = await _persist_answer(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        answer_id = AnswerId(answer.id)
        repo = SqlAlchemyCommunityAnswerRevisionRepository(db_session)
        revision = CommunityAnswerRevision.create(
            answer_id=answer_id,
            revision_number=1,
            previous_body="The original answer body.",
            author_id=author.id,
        )

        await repo.add(revision)
        await db_session.commit()

        reloaded = await repo.get_by_id(revision.id)
        assert reloaded is not None
        assert reloaded.id == revision.id
        assert reloaded.answer_id == answer_id
        assert reloaded.revision_number == 1
        assert reloaded.previous_body == "The original answer body."
        assert reloaded.author_id == author.id

    async def test_get_by_id_returns_none_for_unknown_revision(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityAnswerRevisionRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_repository_interface_exposes_no_remove_method(self) -> None:
        assert not hasattr(CommunityAnswerRevisionRepository, "remove")
        assert not hasattr(SqlAlchemyCommunityAnswerRevisionRepository, "remove")


class TestCommunityAnswerRevisionListByAnswer:
    async def test_lists_only_revisions_for_the_requested_answer(
        self, db_session: AsyncSession
    ) -> None:
        answer, organization_id = await _persist_answer(db_session)
        other_answer, other_organization_id = await _persist_answer(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        other_author = await persist_user(db_session, organization_id=other_organization_id)
        repo = SqlAlchemyCommunityAnswerRevisionRepository(db_session)
        mine = CommunityAnswerRevision.create(
            answer_id=AnswerId(answer.id),
            revision_number=1,
            previous_body="Mine.",
            author_id=author.id,
        )
        not_mine = CommunityAnswerRevision.create(
            answer_id=AnswerId(other_answer.id),
            revision_number=1,
            previous_body="Not mine.",
            author_id=other_author.id,
        )
        await repo.add(mine)
        await repo.add(not_mine)
        await db_session.commit()

        results = await repo.list_by_answer(answer.id)
        ids = [r.id for r in results]
        assert mine.id in ids
        assert not_mine.id not in ids

    async def test_orders_by_revision_number_descending(self, db_session: AsyncSession) -> None:
        answer, organization_id = await _persist_answer(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        repo = SqlAlchemyCommunityAnswerRevisionRepository(db_session)
        for number in (1, 2, 3):
            revision = CommunityAnswerRevision.create(
                answer_id=AnswerId(answer.id),
                revision_number=number,
                previous_body=f"body {number}",
                author_id=author.id,
            )
            await repo.add(revision)
        await db_session.commit()

        results = await repo.list_by_answer(answer.id)
        assert [r.revision_number for r in results] == [3, 2, 1]

    async def test_respects_limit_and_offset(self, db_session: AsyncSession) -> None:
        answer, organization_id = await _persist_answer(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        repo = SqlAlchemyCommunityAnswerRevisionRepository(db_session)
        for number in range(1, 4):
            revision = CommunityAnswerRevision.create(
                answer_id=AnswerId(answer.id),
                revision_number=number,
                previous_body=f"body {number}",
                author_id=author.id,
            )
            await repo.add(revision)
        await db_session.commit()

        results = await repo.list_by_answer(answer.id, offset=1, limit=1)
        assert len(results) == 1


class TestCommunityAnswerUpdateContentPersistsARevision:
    """End-to-end workflow: editing a published answer's body persists
    both the updated live answer and its own archived revision snapshot,
    in the same shape `UpdateAnswerService` performs — see that
    service's own docstring."""

    async def test_editing_a_published_answer_persists_a_revision(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        answers = SqlAlchemyCommunityAnswerRepository(db_session)
        revisions = SqlAlchemyCommunityAnswerRevisionRepository(db_session)
        answer = CommunityAnswer.create(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
            body=AnswerBody("Original body."),
        )
        answer.publish()
        await answers.add(answer)
        await db_session.commit()

        revision = answer.update_content(body=AnswerBody("Edited body."))
        assert revision is not None
        await answers.add(answer)
        await revisions.add(revision)
        await db_session.commit()

        reloaded_answer = await answers.get_by_id(answer.id)
        reloaded_revisions = await revisions.list_by_answer(answer.id)
        assert reloaded_answer is not None
        assert str(reloaded_answer.body) == "Edited body."
        assert reloaded_answer.revision_number == 2
        assert len(reloaded_revisions) == 1
        assert reloaded_revisions[0].previous_body == "Original body."
