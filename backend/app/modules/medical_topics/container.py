"""Module composition root.

The one place `TopicQueryPort` gets bound to its concrete implementation
(`TopicFacade`), and repository interfaces get bound to their SQLAlchemy
implementations. Any future module's own dependency wiring calls
`build_topic_facade(session)` rather than constructing `TopicFacade` (or
any repository) directly — the same per-request factory shape
`app.modules.community.container.build_community_facade` already
establishes for itself, and for the same reason: this module persists
real rows through a real `AsyncSession`, so the facade must be
constructed once per request (or per Celery task), sharing that
session/transaction with every repository it builds.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.medical_topics.application.services.topic_query_service import GetTopicService
from app.modules.medical_topics.infrastructure.repositories import (
    SqlAlchemyMedicalTopicRepository,
)
from app.modules.medical_topics.public.facade import TopicFacade


def build_topic_facade(session: AsyncSession) -> TopicFacade:
    """Construct a `TopicFacade` wired to `session`."""
    topic_repository = SqlAlchemyMedicalTopicRepository(session)
    query_service = GetTopicService(topic_repository=topic_repository)
    return TopicFacade(query_service=query_service)
