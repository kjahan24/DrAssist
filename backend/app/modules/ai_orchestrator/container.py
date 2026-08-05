"""Module composition root for the AI Healthcare Orchestrator module —
the final module of Phase 4.

Scope note — this task builds a **coordination-only** module: it
sequences calls to twelve already-completed peer AI modules' own public
facades and composes their own outputs into one `WorkflowResult`; it
never makes a direct LLM call of its own, never persists anything, and
never replaces any one of those twelve peer modules' own clinical
decision-support scope. Owns no database session or per-request state,
so every component here is process-lifetime and exposed as an
`lru_cache`d singleton, the same shape every prior AI module's own
`container.py` uses for itself.

**Why "AI Foundation" and "AI Clinical Copilot" are not orchestrated
workflow steps** — this task's own ORCHESTRATE section names fourteen
modules, but `domain/enums.py::WorkflowModule` has only twelve members.
Both omitted modules are genuinely reused here (this task's own REUSE
section: "Reuse ALL existing AI modules exactly as they are"), just not
as independently-executable `WorkflowModule` steps:

- **AI Foundation** (`app.modules.ai`) is the substrate every one of the
  twelve orchestrated peer modules is *already* built on — each
  adapter's own peer facade call already goes through AI Foundation's
  `AIGatewayPort`/`PromptRegistry` internally, exactly as it would
  outside a workflow. There is no separate "AI Foundation step" to run;
  reusing it *transitively*, twelve times over, is the whole point of
  this module existing at all.
- **AI Clinical Copilot** (`app.modules.ai_copilot`) was investigated
  directly. Its own public port,
  `app.modules.ai_copilot.public.interfaces.ClinicalCopilotPort.execute`,
  takes an `AIRequest` whose own `request_type: str` + `prompt_version:
  int` must name a prompt template pair (`"{request_type}.system"`/
  `".developer"`/`".user"`) already registered in AI Foundation's own
  `PromptRegistry` — that peer module's own docstring is explicit that
  "this port has no knowledge of what any `request_type` actually
  means" and expects "future clinical-feature modules" to register
  their *own* templates under their own meaning. This orchestrator has
  no prompt templates of its own to register, and inventing one just to
  give `ClinicalCopilotPort.execute` something to call would be
  fabricating a capability this task never asked for — exactly the
  "forced integration produces something worse than no integration"
  failure mode `docs/backend-architecture/10_module_communication.md`
  warns against, the same reasoning every prior AI module's own
  container.py documents when it investigates and declines a
  superficially-relevant peer capability that does not actually fit.

**Why `WorkflowResultComposerService`'s own `confidence_summary` does
not reuse `MedicalReasoningAIPort.score_confidence`** — every prior AI
module since Phase 4.9 has genuinely reused that port's own
`score_confidence` method for its own single generation's own
confidence enrichment step. This module investigated the same reuse for
its own "Confidence Summary" OUTPUT field and declined it: that
method's own signature blends *one* generation's own self-reported
confidence against *that same generation's* own supporting/
contradicting evidence counts — it has no natural reading as "average
several already-final confidence scores produced by twelve unrelated
peer generations," and forcing that fit would fabricate evidence counts
this module was never given. `WorkflowResultComposerService` computes a
plain arithmetic mean instead — see that service's own module docstring
for the same reasoning in full. This module therefore has **no**
dependency on `app.modules.medical_reasoning_ai` at all, unlike every
other AI module built since Phase 4.9.

REUSE, for everything else, is satisfied exactly as it was for
`app.modules.patient_education_ai` (see that module's own `container.py`
scope note for the identical reasoning): "Shared audit infrastructure"
is the `structlog`-via-`app.core.logging.get_logger` pattern every prior
AI module's own audit logger already uses. This module needs no prompt
templates, no parser, no validator-of-AI-output, no cost estimator, and
no provider-selection helper of its own — it makes no direct LLM call,
so none of that infrastructure applies here; its own twelve module
adapters (`infrastructure/module_adapters/*.py`) are this module's
entire infrastructure layer.
"""

from functools import lru_cache

from app.modules.ai_orchestrator.application.ports import (
    WorkflowExecutorPort,
    WorkflowOrchestrationAuditLoggerPort,
    WorkflowPlannerPort,
)
from app.modules.ai_orchestrator.application.services.workflow_executor_service import (
    WorkflowExecutorService,
)
from app.modules.ai_orchestrator.application.services.workflow_planner_service import (
    WorkflowPlannerService,
)
from app.modules.ai_orchestrator.application.services.workflow_result_composer_service import (
    WorkflowResultComposerService,
)
from app.modules.ai_orchestrator.application.services.workflow_validation_service import (
    WorkflowValidationService,
)
from app.modules.ai_orchestrator.application.use_cases.execute_healthcare_workflow import (
    ExecuteHealthcareWorkflowUseCase,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from app.modules.ai_orchestrator.infrastructure.audit.audit_logger import (
    StructlogWorkflowOrchestrationAuditLogger,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.clinical_note_adapter import (
    ClinicalNoteWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.differential_diagnosis_adapter import (  # noqa: E501
    DifferentialDiagnosisWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.drug_interaction_adapter import (
    DrugInteractionWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.icd10_coding_adapter import (
    ICD10CodingWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.lab_interpretation_adapter import (
    LabInterpretationWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.medical_reasoning_adapter import (
    MedicalReasoningWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.pathology_interpretation_adapter import (  # noqa: E501
    PathologyInterpretationWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.patient_education_adapter import (
    PatientEducationWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.prescription_adapter import (
    PrescriptionWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.radiology_interpretation_adapter import (  # noqa: E501
    RadiologyInterpretationWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.risk_stratification_adapter import (  # noqa: E501
    RiskStratificationWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters.soap_note_adapter import (
    SOAPNoteWorkflowAdapter,
)
from app.modules.ai_orchestrator.infrastructure.planning.topological_workflow_planner import (
    DeterministicWorkflowPlanner,
)
from app.modules.ai_orchestrator.public.facade import HealthcareOrchestratorFacade
from app.modules.clinical_note_ai.container import get_clinical_note_ai_facade
from app.modules.differential_diagnosis_ai.container import get_differential_diagnosis_ai_facade
from app.modules.drug_interaction_ai.container import get_drug_interaction_ai_facade
from app.modules.icd10_ai.container import get_icd10_ai_facade
from app.modules.lab_interpretation_ai.container import get_lab_interpretation_ai_facade
from app.modules.medical_reasoning_ai.container import get_medical_reasoning_ai_facade
from app.modules.pathology_interpretation_ai.container import (
    get_pathology_interpretation_ai_facade,
)
from app.modules.patient_education_ai.container import get_patient_education_ai_facade
from app.modules.prescription_ai.container import get_prescription_ai_facade
from app.modules.radiology_interpretation_ai.container import (
    get_radiology_interpretation_ai_facade,
)
from app.modules.risk_stratification_ai.container import get_risk_stratification_ai_facade
from app.modules.soap_note_ai.container import get_soap_note_ai_facade


@lru_cache
def get_workflow_planner_port() -> WorkflowPlannerPort:
    return DeterministicWorkflowPlanner()


@lru_cache
def get_workflow_adapters() -> dict[WorkflowModule, WorkflowExecutorPort]:
    adapters: tuple[WorkflowExecutorPort, ...] = (
        ClinicalNoteWorkflowAdapter(facade=get_clinical_note_ai_facade()),
        SOAPNoteWorkflowAdapter(facade=get_soap_note_ai_facade()),
        ICD10CodingWorkflowAdapter(facade=get_icd10_ai_facade()),
        PrescriptionWorkflowAdapter(facade=get_prescription_ai_facade()),
        DifferentialDiagnosisWorkflowAdapter(facade=get_differential_diagnosis_ai_facade()),
        MedicalReasoningWorkflowAdapter(facade=get_medical_reasoning_ai_facade()),
        LabInterpretationWorkflowAdapter(facade=get_lab_interpretation_ai_facade()),
        RadiologyInterpretationWorkflowAdapter(facade=get_radiology_interpretation_ai_facade()),
        PathologyInterpretationWorkflowAdapter(facade=get_pathology_interpretation_ai_facade()),
        DrugInteractionWorkflowAdapter(facade=get_drug_interaction_ai_facade()),
        RiskStratificationWorkflowAdapter(facade=get_risk_stratification_ai_facade()),
        PatientEducationWorkflowAdapter(facade=get_patient_education_ai_facade()),
    )
    return {adapter.module: adapter for adapter in adapters}


@lru_cache
def get_workflow_validation_service() -> WorkflowValidationService:
    return WorkflowValidationService()


@lru_cache
def get_workflow_planner_service() -> WorkflowPlannerService:
    return WorkflowPlannerService(planner_port=get_workflow_planner_port())


@lru_cache
def get_workflow_executor_service() -> WorkflowExecutorService:
    return WorkflowExecutorService(
        adapters=get_workflow_adapters(),
        validation_service=get_workflow_validation_service(),
    )


@lru_cache
def get_workflow_result_composer_service() -> WorkflowResultComposerService:
    return WorkflowResultComposerService()


@lru_cache
def get_workflow_orchestration_audit_logger() -> WorkflowOrchestrationAuditLoggerPort:
    return StructlogWorkflowOrchestrationAuditLogger()


@lru_cache
def get_execute_healthcare_workflow_use_case() -> ExecuteHealthcareWorkflowUseCase:
    return ExecuteHealthcareWorkflowUseCase(
        validation_service=get_workflow_validation_service(),
        planner_service=get_workflow_planner_service(),
        executor_service=get_workflow_executor_service(),
        composer_service=get_workflow_result_composer_service(),
        audit_logger=get_workflow_orchestration_audit_logger(),
    )


@lru_cache
def get_healthcare_orchestrator_facade() -> HealthcareOrchestratorFacade:
    return HealthcareOrchestratorFacade(execute_use_case=get_execute_healthcare_workflow_use_case())
