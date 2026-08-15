"""`CreateQuestionService` — provisions a new `CommunityQuestion`,
optionally assigning its initial secondary topics/tags in the same call —
the same "one form submission, not N follow-up requests" reasoning
`app.modules.community_posts.application.services.create_post_service
.CreatePostService` already establishes for itself.

Cross-module reads only, never a private repository import:
`CommunityQueryPort.get_community_summary`/`get_membership` resolve the
question's `organization_id` and validate authorship membership;
`TopicQueryPort.topic_exists` validates `primary_topic_id` and each of
`secondary_topic_ids`.

Slug uniqueness is scoped to `(community_id, slug)` — the same
"slugify, then disambiguate on collision" retry loop `CreatePostService
._resolve_unique_slug` already establishes; this loop needs repository
I/O, so it lives here, not on the (pure) `QuestionSlug.from_title`
classmethod.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    CreateQuestionInput,
    CreateQuestionOutput,
)
from app.modules.community_questions.application.services._authorization import (
    ensure_can_create,
)
from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionTag,
    CommunityQuestionTopic,
)
from app.modules.community_questions.domain.exceptions import (
    CommunityNotFoundForQuestionError,
    DuplicateQuestionTagError,
    DuplicateQuestionTopicError,
    TopicNotFoundForQuestionError,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionRepository,
    CommunityQuestionTagRepository,
    CommunityQuestionTopicRepository,
)
from app.modules.community_questions.domain.value_objects import (
    QuestionId,
    QuestionSlug,
    QuestionSummary,
    QuestionTitle,
)
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork

_MAX_SLUG_ATTEMPTS = 50


class CreateQuestionService:
    def __init__(
        self,
        *,
        question_repository: CommunityQuestionRepository,
        question_topic_repository: CommunityQuestionTopicRepository,
        question_tag_repository: CommunityQuestionTagRepository,
        community_query_port: CommunityQueryPort,
        topic_query_port: TopicQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._questions = question_repository
        self._question_topics = question_topic_repository
        self._question_tags = question_tag_repository
        self._communities = community_query_port
        self._topics = topic_query_port
        self._uow = unit_of_work

    async def _resolve_unique_slug(
        self, community_id: UUID, title: str, explicit: str | None
    ) -> QuestionSlug:
        base = QuestionSlug(explicit) if explicit is not None else QuestionSlug.from_title(title)
        candidate = base
        for attempt in range(2, _MAX_SLUG_ATTEMPTS + 2):
            if await self._questions.get_by_slug(community_id, str(candidate)) is None:
                return candidate
            candidate = QuestionSlug(f"{base}-{attempt}")
        return candidate

    async def execute(self, input_dto: CreateQuestionInput) -> CreateQuestionOutput:
        community = await self._communities.get_community_summary(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundForQuestionError(input_dto.community_id)

        member = await self._communities.get_membership(input_dto.community_id, input_dto.author_id)
        ensure_can_create(member, community_id=input_dto.community_id, user_id=input_dto.author_id)

        if not await self._topics.topic_exists(input_dto.primary_topic_id):
            raise TopicNotFoundForQuestionError(input_dto.primary_topic_id)

        for topic_id in input_dto.secondary_topic_ids:
            if not await self._topics.topic_exists(topic_id):
                raise TopicNotFoundForQuestionError(topic_id)

        slug = await self._resolve_unique_slug(
            input_dto.community_id, input_dto.title, input_dto.slug
        )

        question = CommunityQuestion.create(
            community_id=input_dto.community_id,
            organization_id=community.organization_id,
            author_id=input_dto.author_id,
            primary_topic_id=input_dto.primary_topic_id,
            title=QuestionTitle(input_dto.title),
            body=input_dto.body,
            slug=slug,
            summary=QuestionSummary(input_dto.summary) if input_dto.summary is not None else None,
            question_type=input_dto.question_type,
            visibility=input_dto.visibility,
            is_anonymous=input_dto.is_anonymous,
        )

        seen_topic_ids: set[UUID] = {input_dto.primary_topic_id}
        for topic_id in input_dto.secondary_topic_ids:
            if topic_id in seen_topic_ids:
                raise DuplicateQuestionTopicError(question.id, topic_id)
            seen_topic_ids.add(topic_id)

        seen_tags: set[str] = set()
        for tag in input_dto.tags:
            normalized_tag = tag.strip().lower()
            if normalized_tag in seen_tags:
                raise DuplicateQuestionTagError(question.id, normalized_tag)
            seen_tags.add(normalized_tag)

        await self._questions.add(question)
        events = list(question.pull_events())

        question_id = QuestionId(question.id)
        for topic_id in input_dto.secondary_topic_ids:
            assignment = CommunityQuestionTopic.create(question_id=question_id, topic_id=topic_id)
            await self._question_topics.add(assignment)
            events.extend(assignment.pull_events())

        for tag in input_dto.tags:
            tag_assignment = CommunityQuestionTag.create(question_id=question_id, tag=tag)
            await self._question_tags.add(tag_assignment)
            events.extend(tag_assignment.pull_events())

        self._uow.collect_events(events)
        await self._uow.commit()

        return CreateQuestionOutput(
            question_id=question.id,
            community_id=question.community_id,
            slug=str(question.slug),
            title=str(question.title),
            status=question.status,
        )
