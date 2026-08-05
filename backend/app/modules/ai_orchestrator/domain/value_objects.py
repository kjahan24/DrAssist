"""Value objects for the AI Healthcare Orchestrator module's domain.

`WorkflowExecutionInput` is deliberately **generic** relative to the
twelve orchestrated peer modules' own, mutually-incompatible strongly-
typed input value objects (`RiskStratificationInput.vital_signs:
VitalSigns`, `PatientEducationInput.diagnoses`/`.current_medications`,
`LabInterpretationInput.lab_values: tuple[LabValue, ...]`, each
peer module's own `report_text`/`chief_complaint`-based inputs, ...) —
this task's own INPUT section itself only names generic clinical
categories ("Encounter data, Patient data, Clinical notes, Laboratory,
Radiology, Pathology, Medication list, Existing AI outputs"), not any
one peer module's own structured shape. Translating this one generic
bundle into each specific peer's own required shape is
`infrastructure/module_adapters/*.py`'s own job, one file per
`WorkflowModule` — see that package's own module docstring for the full
"what happens when the generic bundle can't satisfy a peer's own
required field" reasoning (the short version: the step is *skipped*,
never fabricated).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.ai_orchestrator.domain.enums import (
    WorkflowModule,
    WorkflowStatus,
    WorkflowStepStatus,
)
from app.modules.ai_orchestrator.domain.exceptions import (
    InvalidWorkflowExecutionInputError,
)
from app.shared.domain.value_object import ValueObject

_MAX_PLAUSIBLE_AGE = 150


@dataclass(frozen=True, slots=True)
class WorkflowExecutionInput(ValueObject):
    organization_id: UUID
    patient_id: UUID
    chief_complaint: str
    visit_id: UUID | None = None
    patient_age: int | None = None
    patient_sex: str | None = None
    language: str = "en"
    encounter_notes: tuple[str, ...] = ()
    clinical_notes: tuple[str, ...] = ()
    soap_notes: tuple[str, ...] = ()
    laboratory_findings: tuple[str, ...] = ()
    radiology_findings: tuple[str, ...] = ()
    pathology_findings: tuple[str, ...] = ()
    medication_list: tuple[str, ...] = ()
    diagnoses: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    symptoms: tuple[str, ...] = ()
    vital_signs: Mapping[str, str] = field(default_factory=dict)
    existing_ai_outputs: Mapping[WorkflowModule, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.chief_complaint.strip():
            raise InvalidWorkflowExecutionInputError("chief_complaint must not be blank")
        if not self.language.strip():
            raise InvalidWorkflowExecutionInputError("language must not be blank")
        if self.patient_age is not None and not (0 <= self.patient_age <= _MAX_PLAUSIBLE_AGE):
            raise InvalidWorkflowExecutionInputError(
                f"patient_age must be between 0 and {_MAX_PLAUSIBLE_AGE} when given"
            )


@dataclass(frozen=True, slots=True)
class WorkflowStepDefinition(ValueObject):
    """One node in a caller-supplied `WorkflowDefinition`'s own graph.

    `required` (default `True`) controls how a *failure* of this step
    affects the overall `WorkflowStatus`: a failed required step can
    only ever produce `PARTIALLY_COMPLETED`/`FAILED`, never
    `COMPLETED`; a failed optional (`required=False`) step is recorded
    exactly the same way (failure isolation applies uniformly) but does
    not by itself prevent an otherwise-successful workflow from being
    reported as `COMPLETED`.
    """

    module: WorkflowModule
    depends_on: tuple[WorkflowModule, ...] = ()
    required: bool = True
    max_retries: int = 0
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise InvalidWorkflowExecutionInputError("max_retries must not be negative")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise InvalidWorkflowExecutionInputError("timeout_seconds must be positive when given")


@dataclass(frozen=True, slots=True)
class WorkflowDefinition(ValueObject):
    """A caller-supplied, configurable execution pipeline, per this
    task's own "Support configurable execution pipelines" requirement.
    Only the shallow Tier-3 checks below happen here — the real graph-
    shape validation (duplicate modules, dangling `depends_on`
    references, circular dependencies) is `WorkflowValidationService`'s
    own job, the same "Tier-3 baseline checks in `__post_init__`; deeper
    checks in a dedicated validator" split every prior AI module's own
    domain exceptions module docstring documents for AI-output
    validation, generalized here to graph validation instead.
    """

    name: str
    steps: tuple[WorkflowStepDefinition, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidWorkflowExecutionInputError("workflow name must not be blank")
        if not self.steps:
            raise InvalidWorkflowExecutionInputError("workflow steps must not be empty")


@dataclass(frozen=True, slots=True)
class WorkflowStepResult(ValueObject):
    """One executed (or skipped/cancelled) step's own outcome — this
    task's own "Module Results" OUTPUT field is `tuple[WorkflowStepResult,
    ...]`.

    `summary` is the step's own peer module's `raw_text` (the exact text
    that peer module's own AI call produced) when the step completed —
    the same value every peer module's own `Generated*.result.raw_text`
    field already carries, reused as-is rather than re-rendered, so
    downstream steps get the fullest available context and no second
    per-step rendering call is needed.
    """

    module: WorkflowModule
    status: WorkflowStepStatus
    summary: str | None = None
    confidence_score: float | None = None
    latency_ms: float = 0.0
    attempt_count: int = 0
    error_message: str | None = None
    skipped_reason: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowResult(ValueObject):
    """The canonical, structured workflow-execution result — this task's
    own nine-item OUTPUT specification, field-for-field: "Workflow
    Summary, Executed Modules, Skipped Modules, Module Results,
    Execution Time, Errors, Warnings, Clinical Summary, Confidence
    Summary"."""

    workflow_name: str
    status: WorkflowStatus
    workflow_summary: str
    executed_modules: tuple[WorkflowModule, ...]
    skipped_modules: tuple[WorkflowModule, ...]
    step_results: tuple[WorkflowStepResult, ...]
    total_execution_time_ms: float
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    clinical_summary: str
    confidence_summary: float | None


@dataclass(frozen=True, slots=True)
class WorkflowExecutionSession(ValueObject):
    """The tracked record of one workflow execution, per this task's own
    "AUDIT — workflow, execution order, latency, module timings,
    failures, retry count" requirement. Deliberately carries no
    `provider`/`model`/token-usage fields the way every orchestrated
    peer module's own `GenerationSession` does — this module makes no
    direct LLM call of its own; each peer step's own AI Foundation call
    is already audited by that peer module's own audit logger, per this
    task's own "Reuse... audit infrastructure" instruction (duplicating
    provider/model/token bookkeeping here would be exactly the
    "duplicate implementation" this task's own REUSE section forbids).
    """

    execution_id: UUID
    workflow_name: str
    execution_order: tuple[WorkflowModule, ...]
    total_latency_ms: float
    module_timings: Mapping[WorkflowModule, float]
    failure_count: int
    retry_count: int
    status: WorkflowStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class WorkflowProgressEvent(ValueObject):
    """One increment of a streamed workflow execution — this task's own
    "Support progressive workflow events" requirement. Reuses the same
    "`AsyncIterator` + `is_final` flag" shape every prior AI module's
    own stream chunk value object establishes for itself, at *step*
    granularity rather than token/word granularity: raw LLM token
    streaming has no meaning at the orchestration level, so "Reuse AI
    Foundation streaming" is satisfied one level down — each individual
    step this event reports on is itself produced by a peer module's own
    generation call, which already went through AI Foundation exactly as
    it would outside a workflow.
    """

    module: WorkflowModule
    status: WorkflowStepStatus
    sequence: int
    is_final: bool = False
