"""Integration tests for `SqlAlchemyCommunityCommentAttachmentRepository`
against a real PostgreSQL instance — round-trip persistence,
`is_assigned`, the unique `(comment_id, document_id)` constraint, and
hard `remove()`.

`community_comment_attachments.comment_id`/`.document_id` are real
foreign keys (`-> community_comments.id`/`-> medical_documents.id`), so
every attachment here is created against an actual persisted
`CommunityComment` and `MedicalDocument`.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_comments._helpers import (
    persist_document,
    persist_org_user_community_post,
    persist_patient,
)

from app.modules.community_comments.domain.entities import (
    CommunityComment,
    CommunityCommentAttachment,
)
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.value_objects import CommentBody, CommentId
from app.modules.community_comments.infrastructure.repositories import (
    SqlAlchemyCommunityCommentAttachmentRepository,
    SqlAlchemyCommunityCommentRepository,
)
from app.modules.documents.domain.entities import MedicalDocument


async def _persist_comment_and_document(
    db_session: AsyncSession,
) -> tuple[CommunityComment, MedicalDocument]:
    organization, user, community, post = await persist_org_user_community_post(db_session)
    comments = SqlAlchemyCommunityCommentRepository(db_session)
    comment = CommunityComment.create(
        target_type=CommentTargetType.POST,
        target_id=post.id,
        community_id=community.id,
        organization_id=organization.id,
        topic_id=None,
        author_id=user.id,
        body=CommentBody("Body."),
    )
    await comments.add(comment)
    await db_session.commit()

    patient = await persist_patient(db_session, organization_id=organization.id)
    document = await persist_document(
        db_session, organization_id=organization.id, patient_id=patient.id, user_id=user.id
    )
    return comment, document


class TestCommunityCommentAttachmentRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        comment, document = await _persist_comment_and_document(db_session)
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)
        attachment = CommunityCommentAttachment.create(
            comment_id=CommentId(comment.id), document_id=document.id
        )

        await repo.add(attachment)
        await db_session.commit()

        reloaded = await repo.get_by_id(attachment.id)
        assert reloaded is not None
        assert reloaded.id == attachment.id
        assert reloaded.comment_id.value == comment.id
        assert reloaded.document_id == document.id

    async def test_get_by_id_returns_none_for_unknown_attachment(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None


class TestCommunityCommentAttachmentListByComment:
    async def test_lists_only_attachments_for_the_requested_comment(
        self, db_session: AsyncSession
    ) -> None:
        comment, document = await _persist_comment_and_document(db_session)
        other_comment, other_document = await _persist_comment_and_document(db_session)
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)
        mine = CommunityCommentAttachment.create(
            comment_id=CommentId(comment.id), document_id=document.id
        )
        not_mine = CommunityCommentAttachment.create(
            comment_id=CommentId(other_comment.id), document_id=other_document.id
        )
        await repo.add(mine)
        await repo.add(not_mine)
        await db_session.commit()

        results = await repo.list_by_comment(comment.id)
        ids = [a.id for a in results]
        assert mine.id in ids
        assert not_mine.id not in ids


class TestCommunityCommentAttachmentIsAssigned:
    async def test_true_when_assigned(self, db_session: AsyncSession) -> None:
        comment, document = await _persist_comment_and_document(db_session)
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)
        attachment = CommunityCommentAttachment.create(
            comment_id=CommentId(comment.id), document_id=document.id
        )
        await repo.add(attachment)
        await db_session.commit()

        assert await repo.is_assigned(comment.id, document.id) is True

    async def test_false_when_not_assigned(self, db_session: AsyncSession) -> None:
        comment, document = await _persist_comment_and_document(db_session)
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)

        assert await repo.is_assigned(comment.id, document.id) is False

    async def test_duplicate_comment_document_pair_violates_the_unique_constraint(
        self, db_session: AsyncSession
    ) -> None:
        comment, document = await _persist_comment_and_document(db_session)
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)
        first = CommunityCommentAttachment.create(
            comment_id=CommentId(comment.id), document_id=document.id
        )
        await repo.add(first)
        await db_session.commit()

        second = CommunityCommentAttachment.create(
            comment_id=CommentId(comment.id), document_id=document.id
        )
        await repo.add(second)
        try:
            await db_session.commit()
            raised = False
        except Exception:  # noqa: BLE001 — asserting *a* DB constraint violation occurs
            raised = True
            await db_session.rollback()
        assert raised is True


class TestCommunityCommentAttachmentRemove:
    async def test_removes_the_attachment(self, db_session: AsyncSession) -> None:
        comment, document = await _persist_comment_and_document(db_session)
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)
        attachment = CommunityCommentAttachment.create(
            comment_id=CommentId(comment.id), document_id=document.id
        )
        await repo.add(attachment)
        await db_session.commit()

        await repo.remove(attachment.id)
        await db_session.commit()

        assert await repo.get_by_id(attachment.id) is None

    async def test_removing_an_unknown_attachment_is_a_no_op(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityCommentAttachmentRepository(db_session)
        await repo.remove(uuid4())
        await db_session.commit()
