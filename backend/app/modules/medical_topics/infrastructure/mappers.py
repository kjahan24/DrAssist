"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`MedicalTopicFollowerModel`/`MedicalTopicAliasModel`/
`MedicalTopicRelationModel` store only `created_at` (see `models.py`'s
own docstring) — their mappers set the domain aggregate's required
`updated_at` field equal to `created_at`, since none of these three
aggregates has a single mutating method that would ever make the two
diverge.
"""

from app.modules.medical_topics.domain.entities import (
    MedicalTopic,
    MedicalTopicAlias,
    MedicalTopicFollower,
    MedicalTopicRelation,
    TopicSpecialty,
)
from app.modules.medical_topics.domain.value_objects import (
    TopicColor,
    TopicDescription,
    TopicId,
    TopicName,
    TopicSlug,
)
from app.modules.medical_topics.infrastructure.models import (
    MedicalTopicAliasModel,
    MedicalTopicFollowerModel,
    MedicalTopicModel,
    MedicalTopicRelationModel,
    TopicSpecialtyModel,
)

# --- MedicalTopic ----------------------------------------------------------------


def medical_topic_to_domain(model: MedicalTopicModel) -> MedicalTopic:
    return MedicalTopic(
        id=model.id,
        slug=TopicSlug(model.slug),
        name=TopicName(model.name),
        description=TopicDescription(model.description) if model.description else None,
        icon=model.icon,
        color=TopicColor(model.color) if model.color else None,
        parent_id=model.parent_id,
        specialty_id=model.specialty_id,
        status=model.status,
        visibility=model.visibility,
        is_featured=model.is_featured,
        trending_score=model.trending_score,
        popularity_score=model.popularity_score,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_medical_topic_to_model(entity: MedicalTopic, model: MedicalTopicModel) -> None:
    model.id = entity.id
    model.slug = str(entity.slug)
    model.name = str(entity.name)
    model.description = str(entity.description) if entity.description is not None else None
    model.icon = entity.icon
    model.color = str(entity.color) if entity.color is not None else None
    model.parent_id = entity.parent_id
    model.specialty_id = entity.specialty_id
    model.status = entity.status
    model.visibility = entity.visibility
    model.is_featured = entity.is_featured
    model.trending_score = entity.trending_score
    model.popularity_score = entity.popularity_score
    model.created_by = entity.created_by
    model.updated_by = entity.updated_by


# --- TopicSpecialty --------------------------------------------------------------


def topic_specialty_to_domain(model: TopicSpecialtyModel) -> TopicSpecialty:
    return TopicSpecialty(
        id=model.id,
        name=TopicName(model.name),
        slug=TopicSlug(model.slug),
        description=TopicDescription(model.description) if model.description else None,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_topic_specialty_to_model(entity: TopicSpecialty, model: TopicSpecialtyModel) -> None:
    model.id = entity.id
    model.name = str(entity.name)
    model.slug = str(entity.slug)
    model.description = str(entity.description) if entity.description is not None else None
    model.is_active = entity.is_active


# --- MedicalTopicFollower ---------------------------------------------------------


def medical_topic_follower_to_domain(model: MedicalTopicFollowerModel) -> MedicalTopicFollower:
    return MedicalTopicFollower(
        id=model.id,
        topic_id=TopicId(model.topic_id),
        user_id=model.user_id,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_medical_topic_follower_to_model(
    entity: MedicalTopicFollower, model: MedicalTopicFollowerModel
) -> None:
    model.id = entity.id
    model.topic_id = entity.topic_id.value
    model.user_id = entity.user_id


# --- MedicalTopicAlias -------------------------------------------------------------


def medical_topic_alias_to_domain(model: MedicalTopicAliasModel) -> MedicalTopicAlias:
    return MedicalTopicAlias(
        id=model.id,
        topic_id=TopicId(model.topic_id),
        alias=TopicName(model.alias),
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_medical_topic_alias_to_model(
    entity: MedicalTopicAlias, model: MedicalTopicAliasModel
) -> None:
    model.id = entity.id
    model.topic_id = entity.topic_id.value
    model.alias = str(entity.alias)


# --- MedicalTopicRelation ----------------------------------------------------------


def medical_topic_relation_to_domain(model: MedicalTopicRelationModel) -> MedicalTopicRelation:
    return MedicalTopicRelation(
        id=model.id,
        topic_id=TopicId(model.topic_id),
        related_topic_id=model.related_topic_id,
        relation_type=model.relation_type,
        created_at=model.created_at,
        updated_at=model.created_at,
    )


def apply_medical_topic_relation_to_model(
    entity: MedicalTopicRelation, model: MedicalTopicRelationModel
) -> None:
    model.id = entity.id
    model.topic_id = entity.topic_id.value
    model.related_topic_id = entity.related_topic_id
    model.relation_type = entity.relation_type
