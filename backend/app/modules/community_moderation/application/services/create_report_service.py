"""`CreateReportService` — files a new `CommunityReport`.

Every report is community-scoped (`community_id` required) even for
`ModerationTargetType.USER`, which has no inherent community of its own —
see `CommunityReport`'s own module docstring. For the five other target
types, `input_dto.community_id` must match the target's own actual
community (mismatches collapse into `ReportTargetNotFoundError`, the same
anti-enumeration posture `_target_resolution.py`'s own docstring
establishes); for `USER`, `input_dto.community_id` is instead validated
directly against `CommunityQueryPort` (it names the community context the
reported behavior occurred in).
"""

from uuid import UUID

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.application.dto import CreateReportInput, ReportSummaryDTO
from app.modules.community_moderation.application.services._authorization import (
    ensure_can_create,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    report_to_summary,
)
from app.modules.community_moderation.application.services._target_resolution import (
    resolve_moderation_target,
)
from app.modules.community_moderation.domain.entities import CommunityReport
from app.modules.community_moderation.domain.enums import ModerationTargetType
from app.modules.community_moderation.domain.exceptions import (
    DuplicateOpenReportError,
    ReportTargetNotFoundError,
)
from app.modules.community_moderation.domain.repositories import CommunityReportRepository
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class CreateReportService:
    def __init__(
        self,
        *,
        report_repository: CommunityReportRepository,
        post_query_port: PostQueryPort,
        question_query_port: QuestionQueryPort,
        answer_query_port: AnswerQueryPort,
        comment_query_port: CommentQueryPort,
        community_query_port: CommunityQueryPort,
        user_query_port: UserQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reports = report_repository
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._communities = community_query_port
        self._users = user_query_port
        self._uow = unit_of_work

    async def _resolve_community_id(self, input_dto: CreateReportInput) -> UUID:
        resolved = await resolve_moderation_target(
            input_dto.target_type,
            input_dto.target_id,
            post_query_port=self._posts,
            question_query_port=self._questions,
            answer_query_port=self._answers,
            comment_query_port=self._comments,
            community_query_port=self._communities,
            user_query_port=self._users,
        )
        if resolved is None or resolved.organization_id != input_dto.organization_id:
            raise ReportTargetNotFoundError(input_dto.target_id)

        if input_dto.target_type is ModerationTargetType.USER:
            community = await self._communities.get_community_summary(input_dto.community_id)
            if community is None or community.organization_id != input_dto.organization_id:
                raise ReportTargetNotFoundError(input_dto.target_id)
            return input_dto.community_id

        if resolved.community_id != input_dto.community_id:
            raise ReportTargetNotFoundError(input_dto.target_id)
        return resolved.community_id

    async def execute(self, input_dto: CreateReportInput) -> ReportSummaryDTO:
        community_id = await self._resolve_community_id(input_dto)

        member = await self._communities.get_membership(community_id, input_dto.reporter_id)
        ensure_can_create(member, community_id=community_id, user_id=input_dto.reporter_id)

        existing = await self._reports.get_open_report(
            input_dto.reporter_id, input_dto.target_type, input_dto.target_id
        )
        if existing is not None:
            raise DuplicateOpenReportError(input_dto.reporter_id, input_dto.target_id)

        report = CommunityReport.create(
            organization_id=input_dto.organization_id,
            community_id=community_id,
            reporter_id=input_dto.reporter_id,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            reason=input_dto.reason,
            description=input_dto.description,
        )
        await self._reports.add(report)
        self._uow.collect_events(report.pull_events())
        await self._uow.commit()
        return report_to_summary(report)
