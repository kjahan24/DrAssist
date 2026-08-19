"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and services for
this module — every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession`. `get_*_query_port` providers each
call the respective peer module's own `build_*_facade(session)`
composition-root factory — never construct a facade directly, the same
rule every prior module's own `presentation/dependencies.py` establishes.
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
from app.modules.community_moderation.application.services.approve_doctor_verification_service import (  # noqa: E501
    ApproveDoctorVerificationService,
)
from app.modules.community_moderation.application.services.assign_report_service import (
    AssignReportService,
)
from app.modules.community_moderation.application.services.create_moderation_action_service import (  # noqa: E501
    CreateModerationActionService,
)
from app.modules.community_moderation.application.services.create_report_service import (
    CreateReportService,
)
from app.modules.community_moderation.application.services.lock_content_service import (
    LockContentService,
)
from app.modules.community_moderation.application.services.reject_doctor_verification_service import (  # noqa: E501
    RejectDoctorVerificationService,
)
from app.modules.community_moderation.application.services.reject_report_service import (
    RejectReportService,
)
from app.modules.community_moderation.application.services.remove_content_service import (
    RemoveContentService,
)
from app.modules.community_moderation.application.services.report_query_service import (
    GetReportService,
    ListReportsService,
)
from app.modules.community_moderation.application.services.request_doctor_verification_service import (  # noqa: E501
    RequestDoctorVerificationService,
)
from app.modules.community_moderation.application.services.resolve_report_service import (
    ResolveReportService,
)
from app.modules.community_moderation.application.services.restore_content_service import (
    RestoreContentService,
)
from app.modules.community_moderation.application.services.restrict_user_service import (
    RestrictUserService,
)
from app.modules.community_moderation.application.services.review_content_service import (
    ReviewContentService,
)
from app.modules.community_moderation.application.services.revoke_doctor_verification_service import (  # noqa: E501
    RevokeDoctorVerificationService,
)
from app.modules.community_moderation.application.services.status_query_service import (
    GetModerationStatusService,
    GetVerificationStatusService,
)
from app.modules.community_moderation.application.services.suspend_user_service import (
    SuspendUserService,
)
from app.modules.community_moderation.application.services.warn_user_service import (
    WarnUserService,
)
from app.modules.community_moderation.domain.repositories import (
    CommunityReportRepository,
    DoctorVerificationRepository,
    ModerationActionRepository,
    ModerationRestrictionRepository,
)
from app.modules.community_moderation.infrastructure.repositories import (
    SqlAlchemyCommunityReportRepository,
    SqlAlchemyDoctorVerificationRepository,
    SqlAlchemyModerationActionRepository,
    SqlAlchemyModerationRestrictionRepository,
)
from app.modules.community_posts.container import build_post_facade
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.container import build_question_facade
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.modules.doctor.container import build_doctor_facade
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_report_repository(session: DbSession) -> CommunityReportRepository:
    return SqlAlchemyCommunityReportRepository(session)


def get_action_repository(session: DbSession) -> ModerationActionRepository:
    return SqlAlchemyModerationActionRepository(session)


def get_restriction_repository(session: DbSession) -> ModerationRestrictionRepository:
    return SqlAlchemyModerationRestrictionRepository(session)


def get_verification_repository(session: DbSession) -> DoctorVerificationRepository:
    return SqlAlchemyDoctorVerificationRepository(session)


def get_post_query_port(session: DbSession) -> PostQueryPort:
    return build_post_facade(session)


def get_question_query_port(session: DbSession) -> QuestionQueryPort:
    return build_question_facade(session)


def get_answer_query_port(session: DbSession) -> AnswerQueryPort:
    return build_answer_facade(session)


def get_comment_query_port(session: DbSession) -> CommentQueryPort:
    return build_comment_facade(session)


def get_community_query_port(session: DbSession) -> CommunityQueryPort:
    return build_community_facade(session)


def get_user_query_port(session: DbSession) -> UserQueryPort:
    return build_authentication_facade(session)


def get_doctor_query_port(session: DbSession) -> DoctorQueryPort:
    return build_doctor_facade(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


ReportRepo = Annotated[CommunityReportRepository, Depends(get_report_repository)]
ActionRepo = Annotated[ModerationActionRepository, Depends(get_action_repository)]
RestrictionRepo = Annotated[ModerationRestrictionRepository, Depends(get_restriction_repository)]
VerificationRepo = Annotated[DoctorVerificationRepository, Depends(get_verification_repository)]
PostPort = Annotated[PostQueryPort, Depends(get_post_query_port)]
QuestionPort = Annotated[QuestionQueryPort, Depends(get_question_query_port)]
AnswerPort = Annotated[AnswerQueryPort, Depends(get_answer_query_port)]
CommentPort = Annotated[CommentQueryPort, Depends(get_comment_query_port)]
CommunityPort = Annotated[CommunityQueryPort, Depends(get_community_query_port)]
UserPort = Annotated[UserQueryPort, Depends(get_user_query_port)]
DoctorPort = Annotated[DoctorQueryPort, Depends(get_doctor_query_port)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_create_report_service(
    report_repository: ReportRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> CreateReportService:
    return CreateReportService(
        report_repository=report_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_report_service(report_repository: ReportRepo) -> GetReportService:
    return GetReportService(report_repository=report_repository)


def get_list_reports_service(report_repository: ReportRepo) -> ListReportsService:
    return ListReportsService(report_repository=report_repository)


def get_assign_report_service(
    report_repository: ReportRepo, community_port: CommunityPort, unit_of_work: Uow
) -> AssignReportService:
    return AssignReportService(
        report_repository=report_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_resolve_report_service(
    report_repository: ReportRepo, community_port: CommunityPort, unit_of_work: Uow
) -> ResolveReportService:
    return ResolveReportService(
        report_repository=report_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_reject_report_service(
    report_repository: ReportRepo, community_port: CommunityPort, unit_of_work: Uow
) -> RejectReportService:
    return RejectReportService(
        report_repository=report_repository,
        community_query_port=community_port,
        unit_of_work=unit_of_work,
    )


def get_create_moderation_action_service(
    action_repository: ActionRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> CreateModerationActionService:
    return CreateModerationActionService(
        action_repository=action_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_review_content_service(
    action_repository: ActionRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> ReviewContentService:
    return ReviewContentService(
        action_repository=action_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_remove_content_service(
    action_repository: ActionRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> RemoveContentService:
    return RemoveContentService(
        action_repository=action_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_restore_content_service(
    action_repository: ActionRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> RestoreContentService:
    return RestoreContentService(
        action_repository=action_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_lock_content_service(
    action_repository: ActionRepo,
    post_port: PostPort,
    question_port: QuestionPort,
    answer_port: AnswerPort,
    comment_port: CommentPort,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> LockContentService:
    return LockContentService(
        action_repository=action_repository,
        post_query_port=post_port,
        question_query_port=question_port,
        answer_query_port=answer_port,
        comment_query_port=comment_port,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_warn_user_service(
    restriction_repository: RestrictionRepo,
    action_repository: ActionRepo,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> WarnUserService:
    return WarnUserService(
        restriction_repository=restriction_repository,
        action_repository=action_repository,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_restrict_user_service(
    restriction_repository: RestrictionRepo,
    action_repository: ActionRepo,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> RestrictUserService:
    return RestrictUserService(
        restriction_repository=restriction_repository,
        action_repository=action_repository,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_suspend_user_service(
    restriction_repository: RestrictionRepo,
    action_repository: ActionRepo,
    community_port: CommunityPort,
    user_port: UserPort,
    unit_of_work: Uow,
) -> SuspendUserService:
    return SuspendUserService(
        restriction_repository=restriction_repository,
        action_repository=action_repository,
        community_query_port=community_port,
        user_query_port=user_port,
        unit_of_work=unit_of_work,
    )


def get_moderation_status_service(
    restriction_repository: RestrictionRepo,
) -> GetModerationStatusService:
    return GetModerationStatusService(restriction_repository=restriction_repository)


def get_request_doctor_verification_service(
    verification_repository: VerificationRepo, doctor_port: DoctorPort, unit_of_work: Uow
) -> RequestDoctorVerificationService:
    return RequestDoctorVerificationService(
        verification_repository=verification_repository,
        doctor_query_port=doctor_port,
        unit_of_work=unit_of_work,
    )


def get_approve_doctor_verification_service(
    verification_repository: VerificationRepo, unit_of_work: Uow
) -> ApproveDoctorVerificationService:
    return ApproveDoctorVerificationService(
        verification_repository=verification_repository, unit_of_work=unit_of_work
    )


def get_reject_doctor_verification_service(
    verification_repository: VerificationRepo, unit_of_work: Uow
) -> RejectDoctorVerificationService:
    return RejectDoctorVerificationService(
        verification_repository=verification_repository, unit_of_work=unit_of_work
    )


def get_revoke_doctor_verification_service(
    verification_repository: VerificationRepo, unit_of_work: Uow
) -> RevokeDoctorVerificationService:
    return RevokeDoctorVerificationService(
        verification_repository=verification_repository, unit_of_work=unit_of_work
    )


def get_verification_status_service(
    verification_repository: VerificationRepo,
) -> GetVerificationStatusService:
    return GetVerificationStatusService(verification_repository=verification_repository)


CreateReportUseCase = Annotated[CreateReportService, Depends(get_create_report_service)]
GetReportQS = Annotated[GetReportService, Depends(get_report_service)]
ListReportsQS = Annotated[ListReportsService, Depends(get_list_reports_service)]
AssignReportUseCase = Annotated[AssignReportService, Depends(get_assign_report_service)]
ResolveReportUseCase = Annotated[ResolveReportService, Depends(get_resolve_report_service)]
RejectReportUseCase = Annotated[RejectReportService, Depends(get_reject_report_service)]
CreateModerationActionUseCase = Annotated[
    CreateModerationActionService, Depends(get_create_moderation_action_service)
]
ReviewContentUseCase = Annotated[ReviewContentService, Depends(get_review_content_service)]
RemoveContentUseCase = Annotated[RemoveContentService, Depends(get_remove_content_service)]
RestoreContentUseCase = Annotated[RestoreContentService, Depends(get_restore_content_service)]
LockContentUseCase = Annotated[LockContentService, Depends(get_lock_content_service)]
WarnUserUseCase = Annotated[WarnUserService, Depends(get_warn_user_service)]
RestrictUserUseCase = Annotated[RestrictUserService, Depends(get_restrict_user_service)]
SuspendUserUseCase = Annotated[SuspendUserService, Depends(get_suspend_user_service)]
GetModerationStatusQS = Annotated[
    GetModerationStatusService, Depends(get_moderation_status_service)
]
RequestDoctorVerificationUseCase = Annotated[
    RequestDoctorVerificationService, Depends(get_request_doctor_verification_service)
]
ApproveDoctorVerificationUseCase = Annotated[
    ApproveDoctorVerificationService, Depends(get_approve_doctor_verification_service)
]
RejectDoctorVerificationUseCase = Annotated[
    RejectDoctorVerificationService, Depends(get_reject_doctor_verification_service)
]
RevokeDoctorVerificationUseCase = Annotated[
    RevokeDoctorVerificationService, Depends(get_revoke_doctor_verification_service)
]
GetVerificationStatusQS = Annotated[
    GetVerificationStatusService, Depends(get_verification_status_service)
]
