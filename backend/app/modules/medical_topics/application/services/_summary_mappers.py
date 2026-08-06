"""Domain entity -> summary DTO mappers shared by every query-style
service in this package — kept in one place so there is exactly one
mapping per entity, matching the "exactly one definition of each shape"
precedent `app.modules.community.application.services._summary_mappers`
already establishes for itself.
"""

from app.modules.medical_topics.application.dto import (
    TopicAliasSummaryDTO,
    TopicFollowerSummaryDTO,
    TopicRelationSummaryDTO,
    TopicSpecialtySummaryDTO,
    TopicSummaryDTO,
)
from app.modules.medical_topics.domain.entities import (
    MedicalTopic,
    MedicalTopicAlias,
    MedicalTopicFollower,
    MedicalTopicRelation,
    TopicSpecialty,
)


def topic_to_summary(topic: MedicalTopic) -> TopicSummaryDTO:
    return TopicSummaryDTO(
        topic_id=topic.id,
        slug=str(topic.slug),
        name=str(topic.name),
        status=topic.status,
        visibility=topic.visibility,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
        description=str(topic.description) if topic.description is not None else None,
        icon=topic.icon,
        color=str(topic.color) if topic.color is not None else None,
        parent_id=topic.parent_id,
        specialty_id=topic.specialty_id,
        is_featured=topic.is_featured,
        trending_score=topic.trending_score,
        popularity_score=topic.popularity_score,
        created_by=topic.created_by,
    )


def follower_to_summary(follower: MedicalTopicFollower) -> TopicFollowerSummaryDTO:
    return TopicFollowerSummaryDTO(
        follower_id=follower.id,
        topic_id=follower.topic_id.value,
        user_id=follower.user_id,
        followed_at=follower.created_at,
    )


def specialty_to_summary(specialty: TopicSpecialty) -> TopicSpecialtySummaryDTO:
    return TopicSpecialtySummaryDTO(
        specialty_id=specialty.id,
        name=str(specialty.name),
        slug=str(specialty.slug),
        is_active=specialty.is_active,
        description=str(specialty.description) if specialty.description is not None else None,
    )


def alias_to_summary(alias: MedicalTopicAlias) -> TopicAliasSummaryDTO:
    return TopicAliasSummaryDTO(
        alias_id=alias.id, topic_id=alias.topic_id.value, alias=str(alias.alias)
    )


def relation_to_summary(relation: MedicalTopicRelation) -> TopicRelationSummaryDTO:
    return TopicRelationSummaryDTO(
        relation_id=relation.id,
        topic_id=relation.topic_id.value,
        related_topic_id=relation.related_topic_id,
        relation_type=relation.relation_type.value,
    )
