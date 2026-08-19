"""In-memory test doubles for the Community AI Features module's one
repository, Unit of Work, and the six cross-module/module-owned ports it
depends on (`PostQueryPort`/`QuestionQueryPort`/`AnswerQueryPort`/
`CommentQueryPort`/`CommunityQueryPort`/`ModerationQueryPort`/
`CommunityAIGeneratorPort`/`SimilarDiscussionSearchPort`/
`TrustedResourceCatalogPort`) — each implements the exact same interface
its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer service tests depend on these, never
on a real database, a real peer module, or a real AI/vector-store call.
"""

import base64
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol, TypeVar
from uuid import UUID, uuid4

from app.modules.ai.public.dto import (
    AIFinishReason,
    AIMessage,
    AIMessageRole,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    PromptVariables,
    TokenUsage,
)
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
    CommunitySummaryDTO,
    CommunityVisibility,
)
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_ai.application.dto import GenerationMetadata
from app.modules.community_ai.application.ports import (
    CommunityAIGeneratorPort,
    SimilarDiscussionSearchPort,
    TrustedResourceCatalogPort,
)
from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_ai.domain.value_objects import (
    CommunityDiscussionSummary,
    MisinformationAssessment,
    SimilarDiscussion,
    TrustedMedicalSource,
    TrustedResourceRecommendation,
)
from app.modules.community_answers.public.dto import (
    AnswerStatus,
    AnswerVisibility,
    CommunityAnswerSummaryDTO,
)
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.dto import (
    CommentStatus,
    CommentTargetType,
    CommunityCommentSummaryDTO,
)
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.domain.value_objects import UserModerationStatus
from app.modules.community_moderation.public.dto import ModerationTargetType, VerificationSummaryDTO
from app.modules.community_moderation.public.interfaces import ModerationQueryPort
from app.modules.community_posts.public.dto import (
    CommunityPostSummaryDTO,
    PostStatus,
    PostType,
    PostVisibility,
)
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.dto import (
    CommunityQuestionSummaryDTO,
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_CURSOR_SEPARATOR = "|"


def _encode_cursor(created_at: datetime, row_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{row_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, row_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(row_id_raw)


# --- Summary DTO builders --------------------------------------------------------------


def make_post_summary(**overrides: object) -> CommunityPostSummaryDTO:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "post_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "slug": "discussion-post",
        "title": "A discussion post",
        "body": "Body text.",
        "excerpt": "Excerpt.",
        "post_type": PostType.DISCUSSION,
        "status": PostStatus.PUBLISHED,
        "visibility": PostVisibility.PUBLIC,
        "is_anonymous": False,
        "is_pinned": False,
        "is_locked": False,
        "is_featured": False,
        "read_time_minutes": 1,
        "view_count": 0,
        "bookmark_count": 0,
        "share_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CommunityPostSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_question_summary(**overrides: object) -> CommunityQuestionSummaryDTO:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "primary_topic_id": uuid4(),
        "slug": "how-to-manage-hypertension",
        "title": "How to manage hypertension?",
        "body": "Body text.",
        "summary": "Summary text.",
        "question_type": QuestionType.GENERAL,
        "status": QuestionStatus.PUBLISHED,
        "visibility": QuestionVisibility.PUBLIC,
        "is_anonymous": False,
        "is_pinned": False,
        "is_featured": False,
        "read_time_minutes": 1,
        "view_count": 0,
        "follower_count": 0,
        "bookmark_count": 0,
        "share_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CommunityQuestionSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_answer_summary(**overrides: object) -> CommunityAnswerSummaryDTO:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "answer_id": uuid4(),
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
        "body": "Body text.",
        "summary": "Summary text.",
        "status": AnswerStatus.PUBLISHED,
        "visibility": AnswerVisibility.PUBLIC,
        "is_anonymous": False,
        "is_best_answer": False,
        "is_featured": False,
        "is_pinned": False,
        "view_count": 0,
        "share_count": 0,
        "revision_number": 1,
        "created_at": now,
        "updated_at": now,
        "author_id": uuid4(),
    }
    defaults.update(overrides)
    return CommunityAnswerSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_comment_summary(**overrides: object) -> CommunityCommentSummaryDTO:
    now = datetime.now(UTC)
    comment_id = uuid4()
    defaults: dict[str, object] = {
        "comment_id": comment_id,
        "target_type": CommentTargetType.POST,
        "target_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "body": "Body text.",
        "status": CommentStatus.PUBLISHED,
        "is_anonymous": False,
        "root_comment_id": comment_id,
        "depth": 0,
        "revision_number": 1,
        "created_at": now,
        "updated_at": now,
        "author_id": uuid4(),
    }
    defaults.update(overrides)
    return CommunityCommentSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_community_summary(**overrides: object) -> CommunitySummaryDTO:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "slug": "oncology",
        "name": "Oncology",
        "visibility": CommunityVisibility.PUBLIC,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CommunitySummaryDTO(**defaults)  # type: ignore[arg-type]


def make_member_summary(**overrides: object) -> CommunityMemberSummaryDTO:
    defaults: dict[str, object] = {
        "member_id": uuid4(),
        "community_id": uuid4(),
        "user_id": uuid4(),
        "role": CommunityRole.MEMBER,
        "status": CommunityMemberStatus.ACTIVE,
        "joined_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return CommunityMemberSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_summary(**overrides: object) -> CommunityDiscussionSummary:
    defaults: dict[str, object] = {
        "key_points": ("Point one.",),
        "main_claims": ("Claim one.",),
        "areas_of_agreement": (),
        "areas_of_disagreement": (),
        "unanswered_questions": (),
        "safety_disclaimer": None,
    }
    defaults.update(overrides)
    return CommunityDiscussionSummary(**defaults)  # type: ignore[arg-type]


def make_misinformation_assessment(**overrides: object) -> MisinformationAssessment:
    from app.modules.community_ai.domain.enums import MisinformationRiskLevel

    defaults: dict[str, object] = {
        "risk_level": MisinformationRiskLevel.LOW,
        "claims": (),
        "evidence_needed": False,
        "explanation": "No concerning claims found.",
        "confidence_score": 0.9,
        "recommended_for_moderation_review": False,
        "reference_suggestions": (),
    }
    defaults.update(overrides)
    return MisinformationAssessment(**defaults)  # type: ignore[arg-type]


def make_trusted_source(**overrides: object) -> TrustedMedicalSource:
    from app.modules.community_ai.domain.enums import ResourceType

    defaults: dict[str, object] = {
        "title": "MedlinePlus",
        "url": "https://medlineplus.gov",
        "resource_type": ResourceType.WEBSITE,
        "topic_tags": ("general health",),
    }
    defaults.update(overrides)
    return TrustedMedicalSource(**defaults)  # type: ignore[arg-type]


def make_resource_recommendation(**overrides: object) -> TrustedResourceRecommendation:
    from app.modules.community_ai.domain.enums import ResourceType

    defaults: dict[str, object] = {
        "source_title": "MedlinePlus",
        "source_url": "https://medlineplus.gov",
        "resource_type": ResourceType.WEBSITE,
        "relevance_explanation": "Directly relevant.",
        "confidence_score": 0.8,
    }
    defaults.update(overrides)
    return TrustedResourceRecommendation(**defaults)  # type: ignore[arg-type]


def make_generation_metadata(**overrides: object) -> GenerationMetadata:
    defaults: dict[str, object] = {"provider": "mock", "model": "mock-model", "latency_ms": 12.5}
    defaults.update(overrides)
    return GenerationMetadata(**defaults)  # type: ignore[arg-type]


# --- Fake query ports --------------------------------------------------------------


class FakePostQueryPort(PostQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityPostSummaryDTO] = {}

    def add_post(self, summary: CommunityPostSummaryDTO) -> None:
        self._summaries[summary.post_id] = summary

    async def post_exists(self, post_id: UUID) -> bool:
        return post_id in self._summaries

    async def get_post_summary(self, post_id: UUID) -> CommunityPostSummaryDTO | None:
        return self._summaries.get(post_id)


class FakeQuestionQueryPort(QuestionQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityQuestionSummaryDTO] = {}

    def add_question(self, summary: CommunityQuestionSummaryDTO) -> None:
        self._summaries[summary.question_id] = summary

    async def question_exists(self, question_id: UUID) -> bool:
        return question_id in self._summaries

    async def get_question_summary(self, question_id: UUID) -> CommunityQuestionSummaryDTO | None:
        return self._summaries.get(question_id)


class FakeAnswerQueryPort(AnswerQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityAnswerSummaryDTO] = {}

    def add_answer(self, summary: CommunityAnswerSummaryDTO) -> None:
        self._summaries[summary.answer_id] = summary

    async def answer_exists(self, answer_id: UUID) -> bool:
        return answer_id in self._summaries

    async def get_answer_summary(self, answer_id: UUID) -> CommunityAnswerSummaryDTO | None:
        return self._summaries.get(answer_id)


class FakeCommentQueryPort(CommentQueryPort):
    def __init__(self) -> None:
        self._summaries: dict[UUID, CommunityCommentSummaryDTO] = {}

    def add_comment(self, summary: CommunityCommentSummaryDTO) -> None:
        self._summaries[summary.comment_id] = summary

    async def comment_exists(self, comment_id: UUID) -> bool:
        return comment_id in self._summaries

    async def get_comment_summary(self, comment_id: UUID) -> CommunityCommentSummaryDTO | None:
        return self._summaries.get(comment_id)

    async def get_thread_summaries(self, root_comment_id: UUID) -> list[CommunityCommentSummaryDTO]:
        root = self._summaries.get(root_comment_id)
        if root is None:
            return []
        return [s for s in self._summaries.values() if s.root_comment_id == root.root_comment_id]


class FakeCommunityQueryPort(CommunityQueryPort):
    def __init__(self) -> None:
        self._communities: dict[UUID, CommunitySummaryDTO] = {}
        self._memberships: dict[tuple[UUID, UUID], CommunityMemberSummaryDTO] = {}

    def add_community(self, summary: CommunitySummaryDTO) -> None:
        self._communities[summary.community_id] = summary

    def add_membership(self, summary: CommunityMemberSummaryDTO) -> None:
        self._memberships[(summary.community_id, summary.user_id)] = summary

    async def community_exists(self, community_id: UUID) -> bool:
        return community_id in self._communities

    async def get_community_summary(self, community_id: UUID) -> CommunitySummaryDTO | None:
        return self._communities.get(community_id)

    async def get_membership(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMemberSummaryDTO | None:
        return self._memberships.get((community_id, user_id))

    async def is_active_member(self, community_id: UUID, user_id: UUID) -> bool:
        member = self._memberships.get((community_id, user_id))
        return member is not None and member.status is CommunityMemberStatus.ACTIVE


class FakeModerationQueryPort(ModerationQueryPort):
    def __init__(self) -> None:
        self._statuses: dict[tuple[ModerationTargetType, UUID], str] = {}

    def set_content_status(
        self, target_type: ModerationTargetType, target_id: UUID, status: str
    ) -> None:
        self._statuses[(target_type, target_id)] = status

    async def get_content_moderation_status(
        self, target_type: ModerationTargetType, target_id: UUID
    ) -> str:
        return self._statuses.get((target_type, target_id), "active")

    async def get_user_moderation_status(
        self, user_id: UUID, *, community_id: UUID | None = None
    ) -> UserModerationStatus:
        return UserModerationStatus(
            user_id=user_id,
            community_id=community_id,
            current_restriction_type=None,
            restricted_until=None,
            active_restriction_count=0,
        )

    async def get_verification_status(self, doctor_id: UUID) -> VerificationSummaryDTO | None:
        return None


# --- Fake generation/search/catalog ports -------------------------------------------


class FakeCommunityAIGeneratorPort(CommunityAIGeneratorPort):
    def __init__(self) -> None:
        self.summary_result: CommunityDiscussionSummary = make_summary()
        self.misinformation_result: MisinformationAssessment = make_misinformation_assessment()
        self.resource_results: tuple[TrustedResourceRecommendation, ...] = ()
        self.metadata: GenerationMetadata = make_generation_metadata()
        self.raise_error: Exception | None = None
        self.calls: list[str] = []

    async def generate_summary(
        self, *, title: str | None, text: str
    ) -> tuple[CommunityDiscussionSummary, GenerationMetadata]:
        self.calls.append("generate_summary")
        if self.raise_error is not None:
            raise self.raise_error
        return self.summary_result, self.metadata

    async def generate_misinformation_assessment(
        self, *, title: str | None, text: str
    ) -> tuple[MisinformationAssessment, GenerationMetadata]:
        self.calls.append("generate_misinformation_assessment")
        if self.raise_error is not None:
            raise self.raise_error
        return self.misinformation_result, self.metadata

    async def generate_resource_recommendations(
        self, *, title: str | None, text: str, catalog: Sequence[TrustedMedicalSource]
    ) -> tuple[tuple[TrustedResourceRecommendation, ...], GenerationMetadata]:
        self.calls.append("generate_resource_recommendations")
        if self.raise_error is not None:
            raise self.raise_error
        return self.resource_results, self.metadata


class FakeSimilarDiscussionSearchPort(SimilarDiscussionSearchPort):
    def __init__(self) -> None:
        self.indexed: list[tuple[CommunityContentTargetType, UUID]] = []
        self.candidates: tuple[SimilarDiscussion, ...] = ()
        self.raise_error: Exception | None = None

    async def index_target(
        self,
        *,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        organization_id: UUID,
        text: str,
    ) -> None:
        if self.raise_error is not None:
            raise self.raise_error
        self.indexed.append((target_type, target_id))

    async def find_similar(
        self,
        *,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        organization_id: UUID,
        limit: int,
    ) -> tuple[SimilarDiscussion, ...]:
        if self.raise_error is not None:
            raise self.raise_error
        return self.candidates[:limit]


class FakeTrustedResourceCatalogPort(TrustedResourceCatalogPort):
    def __init__(self) -> None:
        self.sources: tuple[TrustedMedicalSource, ...] = (make_trusted_source(),)

    async def list_sources(self, *, keywords: Sequence[str] = ()) -> Sequence[TrustedMedicalSource]:
        return self.sources


# --- Fake repository -----------------------------------------------------------------


class FakeAICommunityAnalysisRepository(AICommunityAnalysisRepository):
    def __init__(self) -> None:
        self._analyses: dict[UUID, AICommunityAnalysis] = {}

    async def get_by_id(self, analysis_id: UUID) -> AICommunityAnalysis | None:
        return self._analyses.get(analysis_id)

    async def get_by_target(
        self,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        analysis_type: AIAnalysisType,
    ) -> AICommunityAnalysis | None:
        for analysis in self._analyses.values():
            if (
                analysis.target_type is target_type
                and analysis.target_id == target_id
                and analysis.analysis_type is analysis_type
            ):
                return analysis
        return None

    async def list_analyses(
        self,
        *,
        organization_id: UUID,
        target_type: CommunityContentTargetType | None = None,
        target_id: UUID | None = None,
        analysis_type: AIAnalysisType | None = None,
        status: AIAnalysisStatus | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[AICommunityAnalysis], str | None]:
        matches = [a for a in self._analyses.values() if a.organization_id == organization_id]
        if target_type is not None:
            matches = [a for a in matches if a.target_type is target_type]
        if target_id is not None:
            matches = [a for a in matches if a.target_id == target_id]
        if analysis_type is not None:
            matches = [a for a in matches if a.analysis_type is analysis_type]
        if status is not None:
            matches = [a for a in matches if a.status is status]
        return _paginate(matches, cursor=cursor, limit=limit)

    async def add(self, analysis: AICommunityAnalysis) -> None:
        self._analyses[analysis.id] = analysis


class _HasCreatedAtAndId(Protocol):
    created_at: datetime
    id: UUID


_T = TypeVar("_T", bound=_HasCreatedAtAndId)


def _paginate(
    matches: list[_T], *, cursor: str | None, limit: int
) -> tuple[Sequence[_T], str | None]:
    ordered = sorted(matches, key=lambda m: (m.created_at, m.id), reverse=True)
    if cursor is not None:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        ordered = [m for m in ordered if (m.created_at, m.id) < (cursor_created_at, cursor_id)]
    has_more = len(ordered) > limit
    page = ordered[:limit]
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)
    return page, next_cursor


class FakeAIGateway(AIGatewayPort):
    def __init__(
        self,
        *,
        chat_response: ChatCompletionResponse | None = None,
        rendered_prompts: dict[str, str] | None = None,
        chat_error: Exception | None = None,
    ) -> None:
        self._chat_response = chat_response
        self._rendered_prompts = rendered_prompts or {}
        self._chat_error = chat_error
        self.received_chat_requests: list[ChatCompletionRequest] = []
        self.rendered_calls: list[tuple[str, int | None]] = []

    async def generate_chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        self.received_chat_requests.append(request)
        if self._chat_error is not None:
            raise self._chat_error
        if self._chat_response is not None:
            return self._chat_response
        return ChatCompletionResponse(
            message=AIMessage(role=AIMessageRole.ASSISTANT, content='{"result": "ok"}'),
            model=request.model,
            provider=request.model.provider,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason=AIFinishReason.STOP,
            latency_ms=1.0,
        )

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return EmbeddingResponse(
            embeddings=tuple((0.1, 0.2, 0.3) for _ in request.input_texts),
            model=request.model,
            provider=request.model.provider,
        )

    async def render_prompt(
        self, name: str, variables: PromptVariables, *, version: int | None = None
    ) -> str:
        self.rendered_calls.append((name, version))
        if name in self._rendered_prompts:
            return self._rendered_prompts[name]
        return f"rendered:{name}:v{version}"


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass
