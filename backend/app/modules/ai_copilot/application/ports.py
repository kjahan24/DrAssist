"""Application-layer ports for the AI Clinical Copilot module.

Distinct from, and independent of, AI Foundation's own
`app.modules.ai.application.ports` — this module orchestrates AI Foundation
through its `public/` surface only (`AIGatewayPort`,
`app.modules.ai.public.interfaces`), never its ports directly, per rule 3/4
of this task ("Use only the AI Foundation built previously"; "Everything
must go through AIProvider"). The ports below cover concerns that are
specific to *this* module's own pipeline (structured clinical output
parsing/validation, copilot-level audit) and have no AI Foundation
equivalent reachable from outside that module.
"""

from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID

from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.value_objects import AISession


class CopilotOutputParserPort(ABC):
    @abstractmethod
    def parse(self, raw_text: str, output_format: CopilotOutputFormat) -> object:
        """Raises `StructuredResponseParsingError` (domain) when
        `raw_text` cannot be parsed as `output_format`."""
        ...


class AIResponseValidatorPort(ABC):
    @abstractmethod
    def validate(
        self, parsed_content: object, *, output_format: CopilotOutputFormat, raw_text: str
    ) -> None:
        """Raises `AIResponseValidationError` (domain) when the parsed
        content fails this module's own sanity checks; returns `None`
        (does not itself return a verdict) when valid, per this
        codebase's own "validate-or-raise" convention (e.g. `PromptRenderer
        .render` in AI Foundation)."""
        ...


class CostEstimatorPort(Protocol):
    """A `typing.Protocol`, not an `ABC` — structural, not nominal, typing,
    the same pattern AI Foundation's own `PromptRenderingPort`
    (`app.modules.ai.application.ports`) establishes and for the identical
    reason: `infrastructure/cost/cost_estimator.py::CostEstimator` is a
    plain concrete class (this module has only one implementation and no
    stated need for a second, swappable one — see that module's own
    docstring), but typing `ClinicalCopilotService.__init__`'s
    `cost_estimator` parameter against the concrete class would force
    every test double to subclass it just to satisfy `mypy`. A `Protocol`
    lets both the real `CostEstimator` and a test fake satisfy this type
    structurally, with no inheritance relationship required."""

    def estimate(
        self, *, provider: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float: ...


class CopilotAuditLoggerPort(ABC):
    """Distinct from AI Foundation's own `AIAuditLoggerPort` — that port
    (not reachable from this module; it lives in AI Foundation's
    `application/`, not its `public/`) records "a provider call happened";
    this one records "a clinical copilot orchestration happened", keyed by
    the copilot-specific fields (`request_type`, `patient_id`,
    `prompt_version`) AI Foundation's own audit trail has no way to know
    about. Never logs PHI beyond IDs, matching
    `06_configuration_logging_exceptions.md`'s "PHI is never logged, at
    any layer" rule.
    """

    @abstractmethod
    async def log_session(
        self, session: AISession, *, request_type: str, patient_id: UUID
    ) -> None: ...

    @abstractmethod
    async def log_failure(
        self,
        *,
        request_id: UUID,
        request_type: str,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None: ...
