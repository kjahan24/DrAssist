"""Integration tests for `SqlAlchemyCommunityQuestionRepository` against
a real PostgreSQL instance — round-trip persistence, `search()`
filtering (including the `status != 'deleted'` default exclusion), and
`browse_feed()` cursor (keyset) pagination including the
`pinned_first=True` behavior and the PUBLISHED+CLOSED "live feed" status
inclusion."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_questions._helpers import (
    persist_org_user_community,
    persist_topic,
)

from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.value_objects import QuestionTitle
from app.modules.community_questions.infrastructure.repositories import (
    SqlAlchemyCommunityQuestionRepository,
)


def _make_question(
    *,
    community_id: object,
    organization_id: object,
    author_id: object,
    primary_topic_id: object,
    **overrides: object,
) -> CommunityQuestion:
    defaults: dict[str, object] = {
        "community_id": community_id,
        "organization_id": organization_id,
        "author_id": author_id,
        "primary_topic_id": primary_topic_id,
        "title": QuestionTitle(f"How should hypertension be managed {uuid4().hex[:8]}?"),
        "body": "Detailed clinical question body.",
    }
    defaults.update(overrides)
    return CommunityQuestion.create(**defaults)  # type: ignore[arg-type]


class TestCommunityQuestionRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        question = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
            question_type=QuestionType.CLINICAL,
            visibility=QuestionVisibility.MEMBERS_ONLY,
        )

        await repo.add(question)
        await db_session.commit()

        reloaded = await repo.get_by_id(question.id)
        assert reloaded is not None
        assert reloaded.id == question.id
        assert reloaded.community_id == community.id
        assert reloaded.organization_id == organization.id
        assert reloaded.author_id == user.id
        assert reloaded.primary_topic_id == topic.id
        assert str(reloaded.slug) == str(question.slug)
        assert reloaded.title.value == question.title.value
        assert reloaded.question_type is QuestionType.CLINICAL
        assert reloaded.visibility is QuestionVisibility.MEMBERS_ONLY
        assert reloaded.status is QuestionStatus.DRAFT
        assert reloaded.read_time_minutes >= 1

    async def test_get_by_id_returns_none_for_unknown_question(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_get_by_slug_finds_the_matching_question(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        question = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        await repo.add(question)
        await db_session.commit()

        reloaded = await repo.get_by_slug(community.id, str(question.slug))
        assert reloaded is not None
        assert reloaded.id == question.id

    async def test_add_persists_a_deleted_status_transition(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        question = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        await repo.add(question)
        await db_session.commit()

        question.delete()
        await repo.add(question)
        await db_session.commit()

        reloaded = await repo.get_by_id(question.id)
        assert reloaded is not None
        assert reloaded.status is QuestionStatus.DELETED


class TestCommunityQuestionSearch:
    async def test_scopes_results_to_organization(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        other_org, other_user, other_community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        matching = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        other = _make_question(
            community_id=other_community.id,
            organization_id=other_org.id,
            author_id=other_user.id,
            primary_topic_id=topic.id,
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id)
        ids = [q.id for q in results]
        assert matching.id in ids
        assert other.id not in ids
        assert total >= 1

    async def test_filters_by_question_type(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        clinical = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
            question_type=QuestionType.CLINICAL,
        )
        general = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
            question_type=QuestionType.GENERAL,
        )
        await repo.add(clinical)
        await repo.add(general)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id,
            community_id=community.id,
            question_type=[QuestionType.CLINICAL],
        )
        ids = [q.id for q in results]
        assert clinical.id in ids
        assert general.id not in ids

    async def test_keyword_search_matches_title(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        matching = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
            title=QuestionTitle("Managing Severe Hypotension"),
        )
        other = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
            title=QuestionTitle("Unrelated Topic"),
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id, community_id=community.id, query="Hypotension"
        )
        ids = [q.id for q in results]
        assert matching.id in ids
        assert other.id not in ids

    async def test_excludes_deleted_questions_by_default(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        question = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        await repo.add(question)
        await db_session.commit()
        question.delete()
        await repo.add(question)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, community_id=community.id)
        assert question.id not in [q.id for q in results]

    async def test_include_deleted_true_includes_deleted_questions(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        question = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        await repo.add(question)
        await db_session.commit()
        question.delete()
        await repo.add(question)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id, community_id=community.id, include_deleted=True
        )
        assert question.id in [q.id for q in results]

    async def test_filters_by_primary_topic(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        primary_topic = await persist_topic(db_session)
        other_topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        matching = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=primary_topic.id,
        )
        other = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=other_topic.id,
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id, community_id=community.id, topic_id=primary_topic.id
        )
        ids = [q.id for q in results]
        assert matching.id in ids
        assert other.id not in ids


class TestCommunityQuestionBrowseFeed:
    async def test_returns_only_published_and_closed_questions(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        published = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        published.publish()
        closed = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        closed.publish()
        closed.close()
        draft = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        for q in (published, closed, draft):
            await repo.add(q)
        await db_session.commit()

        items, _ = await repo.browse_feed(
            organization_id=organization.id, community_id=community.id
        )
        ids = {q.id for q in items}
        assert ids == {published.id, closed.id}

    async def test_pinned_question_surfaces_first_on_first_page(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        regular = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        regular.publish()
        pinned = _make_question(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        pinned.publish()
        pinned.set_pinned(True)
        await repo.add(regular)
        await repo.add(pinned)
        await db_session.commit()

        items, _ = await repo.browse_feed(
            organization_id=organization.id, community_id=community.id, pinned_first=True
        )
        assert items[0].id == pinned.id

    async def test_cursor_pagination_covers_all_questions_without_duplicates(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityQuestionRepository(db_session)
        created = []
        for _ in range(5):
            question = _make_question(
                community_id=community.id,
                organization_id=organization.id,
                author_id=user.id,
                primary_topic_id=topic.id,
            )
            question.publish()
            await repo.add(question)
            created.append(question)
        await db_session.commit()

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page, next_cursor = await repo.browse_feed(
                organization_id=organization.id, community_id=community.id, cursor=cursor, limit=2
            )
            seen.extend(q.id for q in page)
            cursor = next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((q.id for q in created), key=str)
        assert len(seen) == len(set(seen))
