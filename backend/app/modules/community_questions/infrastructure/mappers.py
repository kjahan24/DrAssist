"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`CommunityQuestionTopicModel`/`CommunityQuestionTagModel`/
`CommunityQuestionAttachmentModel`/`CommunityQuestionFollowerModel` store
only `created_at` (see `models.py`'s own docstring) — their mappers set
the domain aggregate's required `updated_at` field equal to `created_at`,
since none of these four aggregates has a single mutating method that
would ever make the two diverge.
"""

from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionAttachment,
    CommunityQuestionFollower,
    CommunityQuestionTag,
    CommunityQuestionTopic,
)
from app.modules.community_questions.domain.value_objects import (
    QuestionId,
    QuestionSlug,
    QuestionSummary,
    QuestionTitle,
)
from app.modules.community_questions.infrastructure.models import (
    CommunityQuestionAttachmentModel,
    CommunityQuestionFollowerModel,
    CommunityQuestionModel,
    CommunityQuestionTagModel,
    CommunityQuestionTopicModel,
)

# --- CommunityQuestion -----------------------------------------------------------


def community_question_to_domain(model: CommunityQuestionModel) -> CommunityQuestion:
    return CommunityQuestion(
        id=model.id,
        community_id=model.community_id,
        organization_id=model.organization_id,
        author_id=model.author_id,
        primary_topic_id=model.primary_topic_id,
        slug=QuestionSlug(model.slug),
        title=QuestionTitle(model.title),
        body=model.body,
        summary=QuestionSummary(model.summary),
        question_type=model.question_type,
        status=model.status,
        visibility=model.visibility,
        is_anonymous=model.is_anonymous,
        is_pinned=model.is_pinned,
        is_featured=model.is_featured,
        accepted_answer_id=model.accepted_answer_id,
        read_time_minutes=model.read_time_minutes,
        view_count=model.view_count,
        follower_count=model.follower_count,
        bookmark_count=model.bookmark_count,
        share_count=model.share_count,
        published_at=model.published_at,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_community_question_to_model(
    entity: CommunityQuestion, model: CommunityQuestionModel
) -> None:
    model.id = entity.id
    model.community_id = entity.community_id
    model.organization_id = entity.organization_id
    model.author_id = entity.author_id
    model.primary_topic_id = entity.primary_topic_id
    model.slug = str(entity.slug)
    model.title = str(entity.title)
    model.body = entity.body
    model.summary = str(entity.summary)
    model.question_type = entity.question_type
    model.status = entity.status
    model.visibility = entity.visibility
    model.is_anonymous = entity.is_anonymous
    model.is_pinned = entity.is_pinned
    model.is_featured = entity.is_featured
    model.accepted_answer_id = entity.accepted_answer_id
    model.read_time_minutes = entity.read_time_minutes
    model.view_count = entity.view_count
    model.follower_count = entity.follower_count
    model.bookmark_count = entity.bookmark_count
    model.share_count = entity.share_count
    model.published_at = entity.published_at
    model.updated_by = entity.updated_by


# --- CommunityQuestionTopic --------------------------------------------------------


def community_question_topic_to_domain(
    model: CommunityQuestionTopicModel,
) -> CommunityQuestionTopic:
    return CommunityQuestionTopic(
        id=model.id,
        question_id=QuestionId(model.question_id),
        topic_id=model.topic_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_question_topic_to_model(
    entity: CommunityQuestionTopic, model: CommunityQuestionTopicModel
) -> None:
    model.id = entity.id
    model.question_id = entity.question_id.value
    model.topic_id = entity.topic_id


# --- CommunityQuestionTag ------------------------------------------------------------


def community_question_tag_to_domain(model: CommunityQuestionTagModel) -> CommunityQuestionTag:
    return CommunityQuestionTag(
        id=model.id,
        question_id=QuestionId(model.question_id),
        tag=model.tag,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_question_tag_to_model(
    entity: CommunityQuestionTag, model: CommunityQuestionTagModel
) -> None:
    model.id = entity.id
    model.question_id = entity.question_id.value
    model.tag = entity.tag


# --- CommunityQuestionAttachment -----------------------------------------------------


def community_question_attachment_to_domain(
    model: CommunityQuestionAttachmentModel,
) -> CommunityQuestionAttachment:
    return CommunityQuestionAttachment(
        id=model.id,
        question_id=QuestionId(model.question_id),
        document_id=model.document_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_question_attachment_to_model(
    entity: CommunityQuestionAttachment, model: CommunityQuestionAttachmentModel
) -> None:
    model.id = entity.id
    model.question_id = entity.question_id.value
    model.document_id = entity.document_id


# --- CommunityQuestionFollower -------------------------------------------------------


def community_question_follower_to_domain(
    model: CommunityQuestionFollowerModel,
) -> CommunityQuestionFollower:
    return CommunityQuestionFollower(
        id=model.id,
        question_id=QuestionId(model.question_id),
        user_id=model.user_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_community_question_follower_to_model(
    entity: CommunityQuestionFollower, model: CommunityQuestionFollowerModel
) -> None:
    model.id = entity.id
    model.question_id = entity.question_id.value
    model.user_id = entity.user_id
