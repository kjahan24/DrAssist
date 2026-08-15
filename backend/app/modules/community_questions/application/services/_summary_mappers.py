"""Domain entity -> summary DTO mappers shared by every query-style
service in this package — kept in one place so there is exactly one
mapping per entity, matching the precedent
`app.modules.community_posts.application.services._summary_mappers`
already establishes.
"""

from app.modules.community_questions.application.dto import (
    CommunityQuestionSummaryDTO,
    QuestionAttachmentSummaryDTO,
    QuestionFollowerSummaryDTO,
    QuestionTagSummaryDTO,
    QuestionTopicSummaryDTO,
)
from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionAttachment,
    CommunityQuestionFollower,
    CommunityQuestionTag,
    CommunityQuestionTopic,
)


def question_to_summary(question: CommunityQuestion) -> CommunityQuestionSummaryDTO:
    return CommunityQuestionSummaryDTO(
        question_id=question.id,
        community_id=question.community_id,
        organization_id=question.organization_id,
        author_id=question.author_id,
        primary_topic_id=question.primary_topic_id,
        slug=str(question.slug),
        title=str(question.title),
        body=question.body,
        summary=str(question.summary),
        question_type=question.question_type,
        status=question.status,
        visibility=question.visibility,
        is_anonymous=question.is_anonymous,
        is_pinned=question.is_pinned,
        is_featured=question.is_featured,
        read_time_minutes=question.read_time_minutes,
        view_count=question.view_count,
        follower_count=question.follower_count,
        bookmark_count=question.bookmark_count,
        share_count=question.share_count,
        created_at=question.created_at,
        updated_at=question.updated_at,
        accepted_answer_id=question.accepted_answer_id,
        published_at=question.published_at,
        updated_by=question.updated_by,
    )


def question_topic_to_summary(assignment: CommunityQuestionTopic) -> QuestionTopicSummaryDTO:
    return QuestionTopicSummaryDTO(
        question_topic_id=assignment.id,
        question_id=assignment.question_id.value,
        topic_id=assignment.topic_id,
    )


def question_tag_to_summary(assignment: CommunityQuestionTag) -> QuestionTagSummaryDTO:
    return QuestionTagSummaryDTO(
        question_tag_id=assignment.id,
        question_id=assignment.question_id.value,
        tag=assignment.tag,
    )


def question_attachment_to_summary(
    attachment: CommunityQuestionAttachment,
) -> QuestionAttachmentSummaryDTO:
    return QuestionAttachmentSummaryDTO(
        attachment_id=attachment.id,
        question_id=attachment.question_id.value,
        document_id=attachment.document_id,
    )


def question_follower_to_summary(
    follower: CommunityQuestionFollower,
) -> QuestionFollowerSummaryDTO:
    return QuestionFollowerSummaryDTO(
        follower_id=follower.id,
        question_id=follower.question_id.value,
        user_id=follower.user_id,
    )
