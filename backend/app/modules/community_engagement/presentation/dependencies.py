"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and services
for this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`get_post_query_port`/`get_question_query_port`/`get_answer_query_port`/
`get_comment_query_port`/`get_topic_query_port`/
`get_community_query_port`/`get_user_query_port` each call the
respective peer module's own `build_*_facade(session)` composition-root
factory — never construct a facade (or any of its repositories) directly
— the same rule `app.modules.community_comments.presentation.dependencies`
already establishes for itself.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.authentication.container import build_authentication_facade
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.container import build_community_facade
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.container import build_answer_facade
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.container import build_comment_facade
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_engagement.application.services.cast_vote_service import (
    CastVoteService,
)
from app.modules.community_engagement.application.services.follow_community_service import (
    FollowCommunityService,
)
from app.modules.community_engagement.application.services.follow_doctor_service import (
    FollowDoctorService,
)
from app.modules.community_engagement.application.services.follow_topic_service import (
    FollowTopicService,
)
from app.modules.community_engagement.application.services.list_followers_service import (
    ListFollowersService,
)
from app.modules.community_engagement.application.services.list_following_service import (
    ListFollowingService,
)
from app.modules.community_engagement.application.services.list_saved_content_service import (
    ListSavedContentService,
)
from app.modules.community_engagement.application.services.remove_vote_service import (
    RemoveVoteService,
)
from app.modules.community_engagement.application.services.save_content_service import (
    SaveContentService,
)
from app.modules.community_engagement.application.services.unfollow_community_service import (
    UnfollowCommunityService,
)
from app.modules.community_engagement.application.services.unfollow_doctor_service import (
    UnfollowDoctorService,
)
from app.modules.community_engagement.application.services.unfollow_topic_service import (
    UnfollowTopicService,
)
from app.modules.community_engagement.application.services.unsave_content_service import (
    UnsaveContentService,
)
from app.modules.community_engagement.application.services.vote_query_service import (
    GetVoteCountsService,
    GetVoteStatusService,
)
from app.modules.community_engagement.domain.repositories import (
    CommunityFollowerRepository,
    DoctorFollowerRepository,
    SavedContentRepository,
    TopicFollowerRepository,
    VoteRepository,
)
from app.modules.community_engagement.infrastructure.repositories import (
    SqlAlchemyCommunityFollowerRepository,
    SqlAlchemyDoctorFollowerRepository,
    SqlAlchemySavedContentRepository,
    SqlAlchemyTopicFollowerRepository,
    SqlAlchemyVoteRepository,
)
from app.modules.community_posts.container import build_post_facade
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.container import build_question_facade
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.modules.medical_topics.container import build_topic_facade
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_vote_repository(session: DbSession) -> VoteRepository:
    return SqlAlchemyVoteRepository(session)


def get_saved_content_repository(session: DbSession) -> SavedContentRepository:
    return SqlAlchemySavedContentRepository(session)


def get_topic_follower_repository(session: DbSession) -> TopicFollowerRepository:
    return SqlAlchemyTopicFollowerRepository(session)


def get_community_follower_repository(session: DbSession) -> CommunityFollowerRepository:
    return SqlAlchemyCommunityFollowerRepository(session)


def get_doctor_follower_repository(session: DbSession) -> DoctorFollowerRepository:
    return SqlAlchemyDoctorFollowerRepository(session)


def get_post_query_port(session: DbSession) -> PostQueryPort:
    return build_post_facade(session)


def get_question_query_port(session: DbSession) -> QuestionQueryPort:
    return build_question_facade(session)


def get_answer_query_port(session: DbSession) -> AnswerQueryPort:
    return build_answer_facade(session)


def get_comment_query_port(session: DbSession) -> CommentQueryPort:
    return build_comment_facade(session)


def get_topic_query_port(session: DbSession) -> TopicQueryPort:
    return build_topic_facade(session)


def get_community_query_port(session: DbSession) -> CommunityQueryPort:
    return build_community_facade(session)


def get_user_query_port(session: DbSession) -> UserQueryPort:
    return build_authentication_facade(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


VoteRepo = Annotated[VoteRepository, Depends(get_vote_repository)]
SavedContentRepo = Annotated[SavedContentRepository, Depends(get_saved_content_repository)]
TopicFollowerRepo = Annotated[TopicFollowerRepository, Depends(get_topic_follower_repository)]
CommunityFollowerRepo = Annotated[
    CommunityFollowerRepository, Depends(get_community_follower_repository)
]
DoctorFollowerRepo = Annotated[DoctorFollowerRepository, Depends(get_doctor_follower_repository)]
PostPort = Annotated[PostQueryPort, Depends(get_post_query_port)]
QuestionPort = Annotated[QuestionQueryPort, Depends(get_question_query_port)]
AnswerPort = Annotated[AnswerQueryPort, Depends(get_answer_query_port)]
CommentPort = Annotated[CommentQueryPort, Depends(get_comment_query_port)]
TopicPort = Annotated[TopicQueryPort, Depends(get_topic_query_port)]
CommunityPort = Annotated[CommunityQueryPort, Depends(get_community_query_port)]
UserPort = Annotated[UserQueryPort, Depends(get_user_query_port)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_cast_vote_service(
    vote_repository: VoteRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    unit_of_work: Uow,
) -> CastVoteService:
    return CastVoteService(
        vote_repository=vote_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        unit_of_work=unit_of_work,
    )


def get_remove_vote_service(vote_repository: VoteRepo, unit_of_work: Uow) -> RemoveVoteService:
    return RemoveVoteService(vote_repository=vote_repository, unit_of_work=unit_of_work)


def get_vote_status_service(vote_repository: VoteRepo) -> GetVoteStatusService:
    return GetVoteStatusService(vote_repository=vote_repository)


def get_vote_counts_service(vote_repository: VoteRepo) -> GetVoteCountsService:
    return GetVoteCountsService(vote_repository=vote_repository)


def get_save_content_service(
    saved_content_repository: SavedContentRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    unit_of_work: Uow,
) -> SaveContentService:
    return SaveContentService(
        saved_content_repository=saved_content_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        unit_of_work=unit_of_work,
    )


def get_unsave_content_service(
    saved_content_repository: SavedContentRepo, unit_of_work: Uow
) -> UnsaveContentService:
    return UnsaveContentService(
        saved_content_repository=saved_content_repository, unit_of_work=unit_of_work
    )


def get_list_saved_content_service(
    saved_content_repository: SavedContentRepo,
) -> ListSavedContentService:
    return ListSavedContentService(saved_content_repository=saved_content_repository)


def get_follow_topic_service(
    topic_follower_repository: TopicFollowerRepo, topic_port: TopicPort, unit_of_work: Uow
) -> FollowTopicService:
    return FollowTopicService(
        topic_follower_repository=topic_follower_repository,
        topic_query_port=topic_port,
        unit_of_work=unit_of_work,
    )


def get_unfollow_topic_service(
    topic_follower_repository: TopicFollowerRepo, unit_of_work: Uow
) -> UnfollowTopicService:
    return UnfollowTopicService(
        topic_follower_repository=topic_follower_repository, unit_of_work=unit_of_work
    )


def get_follow_community_service(
    community_follower_repository: CommunityFollowerRepo,
    community_port: CommunityPort,
    unit_of_work: Uow,
) -> FollowCommunityService:
    return FollowCommunityService(
        community_follower_repository=community_follower_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_unfollow_community_service(
    community_follower_repository: CommunityFollowerRepo, unit_of_work: Uow
) -> UnfollowCommunityService:
    return UnfollowCommunityService(
        community_follower_repository=community_follower_repository, unit_of_work=unit_of_work
    )


def get_follow_doctor_service(
    doctor_follower_repository: DoctorFollowerRepo, user_port: UserPort, unit_of_work: Uow
) -> FollowDoctorService:
    return FollowDoctorService(
        doctor_follower_repository=doctor_follower_repository,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_unfollow_doctor_service(
    doctor_follower_repository: DoctorFollowerRepo, unit_of_work: Uow
) -> UnfollowDoctorService:
    return UnfollowDoctorService(
        doctor_follower_repository=doctor_follower_repository, unit_of_work=unit_of_work
    )


def get_list_followers_service(
    topic_follower_repository: TopicFollowerRepo,
    community_follower_repository: CommunityFollowerRepo,
    doctor_follower_repository: DoctorFollowerRepo,
) -> ListFollowersService:
    return ListFollowersService(
        topic_follower_repository=topic_follower_repository,
        community_follower_repository=community_follower_repository,
        doctor_follower_repository=doctor_follower_repository,
    )


def get_list_following_service(
    topic_follower_repository: TopicFollowerRepo,
    community_follower_repository: CommunityFollowerRepo,
    doctor_follower_repository: DoctorFollowerRepo,
) -> ListFollowingService:
    return ListFollowingService(
        topic_follower_repository=topic_follower_repository,
        community_follower_repository=community_follower_repository,
        doctor_follower_repository=doctor_follower_repository,
    )


CastVoteUseCase = Annotated[CastVoteService, Depends(get_cast_vote_service)]
RemoveVoteUseCase = Annotated[RemoveVoteService, Depends(get_remove_vote_service)]
GetVoteStatusQS = Annotated[GetVoteStatusService, Depends(get_vote_status_service)]
GetVoteCountsQS = Annotated[GetVoteCountsService, Depends(get_vote_counts_service)]
SaveContentUseCase = Annotated[SaveContentService, Depends(get_save_content_service)]
UnsaveContentUseCase = Annotated[UnsaveContentService, Depends(get_unsave_content_service)]
ListSavedContentQS = Annotated[ListSavedContentService, Depends(get_list_saved_content_service)]
FollowTopicUseCase = Annotated[FollowTopicService, Depends(get_follow_topic_service)]
UnfollowTopicUseCase = Annotated[UnfollowTopicService, Depends(get_unfollow_topic_service)]
FollowCommunityUseCase = Annotated[FollowCommunityService, Depends(get_follow_community_service)]
UnfollowCommunityUseCase = Annotated[
    UnfollowCommunityService, Depends(get_unfollow_community_service)
]
FollowDoctorUseCase = Annotated[FollowDoctorService, Depends(get_follow_doctor_service)]
UnfollowDoctorUseCase = Annotated[UnfollowDoctorService, Depends(get_unfollow_doctor_service)]
ListFollowersQS = Annotated[ListFollowersService, Depends(get_list_followers_service)]
ListFollowingQS = Annotated[ListFollowingService, Depends(get_list_following_service)]
