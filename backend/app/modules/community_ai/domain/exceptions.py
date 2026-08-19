"""Domain exceptions for the Community AI Features module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422. See that module's own
docstring for the full heuristic.

`AnalysisTargetNotFoundError` is raised for *both* "genuinely doesn't
exist" and "belongs to a different organization / isn't visible to the
caller" — the same deliberate anti-enumeration posture
`app.modules.community_engagement.domain.exceptions
.VoteTargetNotFoundError`'s own docstring establishes: a caller must never
be able to distinguish "this id doesn't exist" from "it exists, but isn't
yours to see."

Errors originating from AI Foundation (`app.modules.ai.public.interfaces
.AIGatewayPort`) — timeouts, rate limits, authentication failures,
provider unavailability (all `AIProviderError` subclasses) — are
deliberately **not** wrapped or re-typed here, matching the documented
precedent every other `*_ai` module in this codebase follows (e.g.
`app.modules.icd10_ai.domain.exceptions`'s own docstring): this module
cannot import `app.modules.ai.domain` to `isinstance`-check or re-wrap
those errors, so they propagate unchanged out of
`infrastructure/generation/community_ai_generator.py`.
"""

from uuid import UUID

from app.modules.community_ai.domain.enums import AIAnalysisType, CommunityContentTargetType
from app.shared.domain.exceptions import DomainError


class AnalysisNotFoundError(DomainError):
    def __init__(self, analysis_id: UUID) -> None:
        self.analysis_id = analysis_id
        super().__init__(f"No AI analysis found with id {analysis_id}.")


class AnalysisTargetNotFoundError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"No analyzable content found with id {target_id}.")


class UnsupportedAnalysisTargetTypeError(DomainError):
    def __init__(
        self, target_type: CommunityContentTargetType, analysis_type: AIAnalysisType
    ) -> None:
        self.target_type = target_type
        self.analysis_type = analysis_type
        super().__init__(
            f"{analysis_type.value!r} analysis does not support target type "
            f"{target_type.value!r}."
        )


class EmptyThreadError(DomainError):
    def __init__(self, root_comment_id: UUID) -> None:
        self.root_comment_id = root_comment_id
        super().__init__(f"No comments found in the thread rooted at {root_comment_id}.")


class AnalysisAlreadyProcessingError(DomainError):
    def __init__(self, analysis_id: UUID) -> None:
        self.analysis_id = analysis_id
        super().__init__(f"Analysis {analysis_id} is already being processed.")


class AnalysisNotProcessingError(DomainError):
    def __init__(self, analysis_id: UUID) -> None:
        self.analysis_id = analysis_id
        super().__init__(f"Analysis {analysis_id} is not currently processing.")


class AnalysisNotYetCompletedError(DomainError):
    def __init__(self, analysis_id: UUID) -> None:
        self.analysis_id = analysis_id
        super().__init__(f"Analysis {analysis_id} has not completed yet.")


class InvalidAnalysisResultError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class EmbeddingUnavailableError(DomainError):
    """Raised by `application/services/find_similar_discussions_service.py`
    when the vector store has no embedding for the source target yet
    (rather than propagating a raw infrastructure error to an end-user
    caller) — see that service's own docstring for the "handle missing
    embeddings gracefully" DOMAIN requirement this backs."""

    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"No embedding is available yet for target {target_id}.")
