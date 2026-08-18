"""Unit tests for `CreateReplyService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_comments.application.dto import CreateReplyInput
from app.modules.community_comments.application.services.create_reply_service import (
    CreateReplyService,
)
from app.modules.community_comments.domain.entities import MAX_COMMENT_DEPTH, CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.events import CommunityCommentCreated
from app.modules.community_comments.domain.exceptions import (
    CommentMembershipRequiredError,
    MaxCommentDepthExceededError,
    ParentCommentNotAcceptingRepliesError,
    ParentCommentNotFoundError,
)
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import (
    FakeCommunityCommentRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        CreateReplyService, FakeCommunityCommentRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    comments = FakeCommunityCommentRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = CreateReplyService(
        comment_repository=comments, community_query_port=communities, unit_of_work=uow
    )
    return service, comments, communities, uow


async def _seed_published_parent(
    comments: FakeCommunityCommentRepository, *, community_id: object
) -> CommunityComment:
    parent = CommunityComment.create(
        target_type=CommentTargetType.POST,
        target_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=None,
        author_id=uuid4(),
        body=CommentBody("Parent body."),
    )
    parent.publish()
    parent.pull_events()
    await comments.add(parent)
    return parent


class TestCreateReply:
    async def test_creates_a_reply(self) -> None:
        service, comments, communities, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        parent = await _seed_published_parent(comments, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            CreateReplyInput(parent_comment_id=parent.id, author_id=author_id, body="A reply.")
        )
        stored = await comments.get_by_id(output.comment_id)
        assert stored is not None
        assert str(stored.body) == "A reply."
        assert stored.parent_comment_id == parent.id

    async def test_inherits_target_and_root_from_the_parent(self) -> None:
        service, comments, communities, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        parent = await _seed_published_parent(comments, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            CreateReplyInput(parent_comment_id=parent.id, author_id=author_id, body="A reply.")
        )
        assert output.root_comment_id == parent.id
        assert output.depth == 1

    async def test_reply_to_a_reply_increments_depth_further(self) -> None:
        service, comments, communities, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        parent = await _seed_published_parent(comments, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        first_reply_output = await service.execute(
            CreateReplyInput(parent_comment_id=parent.id, author_id=author_id, body="First reply.")
        )
        first_reply = await comments.get_by_id(first_reply_output.comment_id)
        assert first_reply is not None
        first_reply.publish()
        first_reply.pull_events()
        await comments.add(first_reply)

        second_output = await service.execute(
            CreateReplyInput(
                parent_comment_id=first_reply.id, author_id=author_id, body="Reply to a reply."
            )
        )
        assert second_output.depth == 2
        assert second_output.root_comment_id == parent.id

    async def test_unknown_parent_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(ParentCommentNotFoundError):
            await service.execute(
                CreateReplyInput(parent_comment_id=uuid4(), author_id=uuid4(), body="A reply.")
            )

    async def test_draft_parent_rejects_new_replies(self) -> None:
        service, comments, communities, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        parent = CommunityComment.create(
            target_type=CommentTargetType.POST,
            target_id=uuid4(),
            community_id=community_id,
            organization_id=uuid4(),
            topic_id=None,
            author_id=uuid4(),
            body=CommentBody("Draft parent."),
        )
        await comments.add(parent)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(ParentCommentNotAcceptingRepliesError):
            await service.execute(
                CreateReplyInput(parent_comment_id=parent.id, author_id=author_id, body="A reply.")
            )

    async def test_archived_parent_rejects_new_replies(self) -> None:
        service, comments, communities, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        parent = await _seed_published_parent(comments, community_id=community_id)
        parent.archive()
        await comments.add(parent)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(ParentCommentNotAcceptingRepliesError):
            await service.execute(
                CreateReplyInput(parent_comment_id=parent.id, author_id=author_id, body="A reply.")
            )

    async def test_non_member_raises(self) -> None:
        service, comments, _, _ = _seeded()
        community_id = uuid4()
        parent = await _seed_published_parent(comments, community_id=community_id)

        with pytest.raises(CommentMembershipRequiredError):
            await service.execute(
                CreateReplyInput(parent_comment_id=parent.id, author_id=uuid4(), body="A reply.")
            )

    async def test_exceeding_max_depth_raises(self) -> None:
        service, comments, communities, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        current = await _seed_published_parent(comments, community_id=community_id)

        for _ in range(MAX_COMMENT_DEPTH):
            output = await service.execute(
                CreateReplyInput(
                    parent_comment_id=current.id, author_id=author_id, body="Nested reply."
                )
            )
            fetched = await comments.get_by_id(output.comment_id)
            assert fetched is not None
            current = fetched
            current.publish()
            current.pull_events()
            await comments.add(current)

        with pytest.raises(MaxCommentDepthExceededError):
            await service.execute(
                CreateReplyInput(
                    parent_comment_id=current.id, author_id=author_id, body="Too deep."
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, comments, communities, uow = _seeded()
        community_id, author_id = uuid4(), uuid4()
        parent = await _seed_published_parent(comments, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            CreateReplyInput(parent_comment_id=parent.id, author_id=author_id, body="A reply.")
        )
        assert uow.committed is True

    async def test_publishes_a_community_comment_created_event(self) -> None:
        service, comments, communities, uow = _seeded()
        community_id, author_id = uuid4(), uuid4()
        parent = await _seed_published_parent(comments, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            CreateReplyInput(parent_comment_id=parent.id, author_id=author_id, body="A reply.")
        )
        assert any(isinstance(e, CommunityCommentCreated) for e in uow.published_events)
