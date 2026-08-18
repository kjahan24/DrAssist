"""Integration tests for `SqlAlchemyCommunityAnswerRepository` against a
real PostgreSQL instance — round-trip persistence, `search()` filtering
(including the `status != 'deleted'` default exclusion and the
best-answer/featured/pinned toggles), `get_best_answer_for_question`, and
`browse_feed()` cursor (keyset) pagination including the
`pinned_first=True` behavior and the PUBLISHED-only "live feed" status
restriction (no CLOSED equivalent for Answers — see that method's own
docstring)."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_answers._helpers import (
    persist_org_user_community_question,
)

from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.domain.value_objects import AnswerBody
from app.modules.community_answers.infrastructure.repositories import (
    SqlAlchemyCommunityAnswerRepository,
)


def _make_answer(
    *,
    question_id: object,
    community_id: object,
    organization_id: object,
    topic_id: object,
    author_id: object,
    **overrides: object,
) -> CommunityAnswer:
    defaults: dict[str, object] = {
        "question_id": question_id,
        "community_id": community_id,
        "organization_id": organization_id,
        "topic_id": topic_id,
        "author_id": author_id,
        "body": AnswerBody(f"Detailed clinical answer body {uuid4().hex[:8]}."),
    }
    defaults.update(overrides)
    return CommunityAnswer.create(**defaults)  # type: ignore[arg-type]


class TestCommunityAnswerRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        answer = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
            visibility=AnswerVisibility.MEMBERS_ONLY,
            is_anonymous=True,
        )

        await repo.add(answer)
        await db_session.commit()

        reloaded = await repo.get_by_id(answer.id)
        assert reloaded is not None
        assert reloaded.id == answer.id
        assert reloaded.question_id == question.id
        assert reloaded.community_id == community.id
        assert reloaded.organization_id == organization.id
        assert reloaded.topic_id == topic.id
        assert reloaded.author_id == user.id
        assert str(reloaded.body) == str(answer.body)
        assert reloaded.visibility is AnswerVisibility.MEMBERS_ONLY
        assert reloaded.is_anonymous is True
        assert reloaded.status is AnswerStatus.DRAFT

    async def test_get_by_id_returns_none_for_unknown_answer(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_add_persists_a_published_status_transition(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        answer = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        await repo.add(answer)
        await db_session.commit()

        answer.publish()
        await repo.add(answer)
        await db_session.commit()

        reloaded = await repo.get_by_id(answer.id)
        assert reloaded is not None
        assert reloaded.status is AnswerStatus.PUBLISHED
        assert reloaded.published_at is not None

    async def test_add_persists_a_deleted_status_transition(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        answer = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        await repo.add(answer)
        await db_session.commit()

        answer.delete()
        await repo.add(answer)
        await db_session.commit()

        reloaded = await repo.get_by_id(answer.id)
        assert reloaded is not None
        assert reloaded.status is AnswerStatus.DELETED


class TestCommunityAnswerGetBestAnswerForQuestion:
    async def test_returns_the_best_answer(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        best = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        best.publish()
        best.mark_as_best()
        other = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        other.publish()
        await repo.add(best)
        await repo.add(other)
        await db_session.commit()

        result = await repo.get_best_answer_for_question(question.id)
        assert result is not None
        assert result.id == best.id

    async def test_returns_none_when_no_best_answer_is_set(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        answer = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        answer.publish()
        await repo.add(answer)
        await db_session.commit()

        assert await repo.get_best_answer_for_question(question.id) is None

    async def test_enforces_only_one_best_answer_per_question_at_the_database_level(
        self, db_session: AsyncSession
    ) -> None:
        """`uq_community_answers_question_id_best` — a DB-level safety net
        on top of `MarkBestAnswerService`'s own application-level
        coordination."""
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        first = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        first.publish()
        first.mark_as_best()
        await repo.add(first)
        await db_session.commit()

        second = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        second.publish()
        second.mark_as_best()
        await repo.add(second)
        try:
            await db_session.commit()
            raised = False
        except Exception:  # noqa: BLE001 — asserting *a* DB constraint violation occurs
            raised = True
            await db_session.rollback()
        assert raised is True


class TestCommunityAnswerSearch:
    async def test_scopes_results_to_organization(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        (
            other_org,
            other_user,
            other_community,
            other_topic,
            other_question,
        ) = await persist_org_user_community_question(db_session)
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        matching = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        other = _make_answer(
            question_id=other_question.id,
            community_id=other_community.id,
            organization_id=other_org.id,
            topic_id=other_topic.id,
            author_id=other_user.id,
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id)
        ids = [a.id for a in results]
        assert matching.id in ids
        assert other.id not in ids
        assert total >= 1

    async def test_filters_by_question(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        (
            other_organization,
            other_user,
            other_community,
            other_topic,
            other_question,
        ) = await persist_org_user_community_question(db_session)
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        matching = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        other = _make_answer(
            question_id=other_question.id,
            community_id=other_community.id,
            organization_id=other_organization.id,
            topic_id=other_topic.id,
            author_id=other_user.id,
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, question_id=question.id)
        ids = [a.id for a in results]
        assert matching.id in ids
        assert other.id not in ids

    async def test_filters_best_answer_only(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        best = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        best.publish()
        best.mark_as_best()
        other = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        await repo.add(best)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, best_answer_only=True)
        ids = [a.id for a in results]
        assert best.id in ids
        assert other.id not in ids

    async def test_filters_featured_only(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        featured = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        featured.set_featured(True)
        other = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        await repo.add(featured)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, featured_only=True)
        ids = [a.id for a in results]
        assert featured.id in ids
        assert other.id not in ids

    async def test_filters_pinned_only(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        pinned = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        pinned.set_pinned(True)
        other = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        await repo.add(pinned)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, pinned_only=True)
        ids = [a.id for a in results]
        assert pinned.id in ids
        assert other.id not in ids

    async def test_keyword_search_matches_body(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        matching = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
            body=AnswerBody("Managing severe hypotension in the ICU."),
        )
        other = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
            body=AnswerBody("Completely unrelated topic."),
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, query="hypotension")
        ids = [a.id for a in results]
        assert matching.id in ids
        assert other.id not in ids

    async def test_excludes_deleted_answers_by_default(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        answer = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        await repo.add(answer)
        await db_session.commit()
        answer.delete()
        await repo.add(answer)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, question_id=question.id)
        assert answer.id not in [a.id for a in results]

    async def test_include_deleted_true_includes_deleted_answers(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        answer = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        await repo.add(answer)
        await db_session.commit()
        answer.delete()
        await repo.add(answer)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id, question_id=question.id, include_deleted=True
        )
        assert answer.id in [a.id for a in results]


class TestCommunityAnswerBrowseFeed:
    async def test_returns_only_published_answers(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        published = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        published.publish()
        draft = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        for a in (published, draft):
            await repo.add(a)
        await db_session.commit()

        items, _ = await repo.browse_feed(organization_id=organization.id, question_id=question.id)
        ids = {a.id for a in items}
        assert ids == {published.id}

    async def test_pinned_answer_surfaces_first_on_first_page(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        regular = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        regular.publish()
        pinned = _make_answer(
            question_id=question.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        pinned.publish()
        pinned.set_pinned(True)
        await repo.add(regular)
        await repo.add(pinned)
        await db_session.commit()

        items, _ = await repo.browse_feed(
            organization_id=organization.id, question_id=question.id, pinned_first=True
        )
        assert items[0].id == pinned.id

    async def test_cursor_pagination_covers_all_answers_without_duplicates(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, topic, question = await persist_org_user_community_question(
            db_session
        )
        repo = SqlAlchemyCommunityAnswerRepository(db_session)
        created = []
        for _ in range(5):
            answer = _make_answer(
                question_id=question.id,
                community_id=community.id,
                organization_id=organization.id,
                topic_id=topic.id,
                author_id=user.id,
            )
            answer.publish()
            await repo.add(answer)
            created.append(answer)
        await db_session.commit()

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page, next_cursor = await repo.browse_feed(
                organization_id=organization.id, question_id=question.id, cursor=cursor, limit=2
            )
            seen.extend(a.id for a in page)
            cursor = next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((a.id for a in created), key=str)
        assert len(seen) == len(set(seen))
