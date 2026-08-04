"""Module composition root for the AI Clinical Copilot.

Scope note — this task builds the **orchestration layer** only: it
coordinates AI requests (context assembly, prompt rendering, the LLM
call through AI Foundation, structured parsing, response validation,
audit logging) but implements no clinical AI feature itself — no SOAP
generation, ICD suggestion, prescription generation, differential
diagnosis, clinical note generation, lab interpretation, or voice AI.
Each of those is a separate future module that will call this one's
`public/interfaces.py::ClinicalCopilotPort` with its own `request_type`
and pre-registered AI Foundation prompt templates
(`"{request_type}.system"`/`.developer`/`.user"`) — none of which this
module registers itself.

Unlike AI Foundation's own `container.py` (session-less — that module
owns no cross-module reads), this module's `ContextBuilder` reads seven
peer modules (Patient, Prescription, Visit, Clinical Note, SOAP Note, Lab
Result, Timeline) through their own request-scoped facades, so
`build_clinical_copilot_facade` takes an `AsyncSession` and is called
fresh per request, the same pattern every DB-backed module's own
`container.py` already establishes (e.g.
`app.modules.family_access.container.build_family_access_facade`). The
AI Foundation gateway itself, and this module's own parser/validator/
audit-logger/cost-estimator, are process-lifetime singletons (`lru_cache`)
since none of them hold per-request state.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.ai.container import get_ai_gateway_facade
from app.modules.ai_copilot.application.ports import (
    AIResponseValidatorPort,
    CopilotAuditLoggerPort,
    CopilotOutputParserPort,
)
from app.modules.ai_copilot.application.services.clinical_copilot_service import (
    ClinicalCopilotService,
)
from app.modules.ai_copilot.application.services.context_builder import ContextBuilder
from app.modules.ai_copilot.application.services.prompt_builder import PromptBuilder
from app.modules.ai_copilot.application.use_cases.execute_copilot_request import (
    ExecuteCopilotRequest,
)
from app.modules.ai_copilot.infrastructure.audit.audit_logger import StructlogCopilotAuditLogger
from app.modules.ai_copilot.infrastructure.cost.cost_estimator import CostEstimator
from app.modules.ai_copilot.infrastructure.parsing.structured_output_parser import (
    DefaultCopilotOutputParser,
)
from app.modules.ai_copilot.infrastructure.provider_selection import resolve_default_ai_model
from app.modules.ai_copilot.infrastructure.validation.response_validator import (
    DefaultAIResponseValidator,
)
from app.modules.ai_copilot.public.facade import ClinicalCopilotFacade
from app.modules.clinical_notes.container import build_clinical_note_facade
from app.modules.lab_results.container import build_lab_result_facade
from app.modules.patient.container import build_patient_facade
from app.modules.prescriptions.container import build_prescription_facade
from app.modules.soap_notes.container import build_soap_note_facade
from app.modules.timeline.container import build_timeline_facade
from app.modules.visit.container import build_visit_facade


@lru_cache
def get_output_parser() -> CopilotOutputParserPort:
    return DefaultCopilotOutputParser()


@lru_cache
def get_response_validator() -> AIResponseValidatorPort:
    return DefaultAIResponseValidator()


@lru_cache
def get_copilot_audit_logger() -> CopilotAuditLoggerPort:
    return StructlogCopilotAuditLogger()


@lru_cache
def get_cost_estimator() -> CostEstimator:
    return CostEstimator()


def build_clinical_copilot_facade(session: AsyncSession) -> ClinicalCopilotFacade:
    context_builder = ContextBuilder(
        patient_query_port=build_patient_facade(session),
        prescription_query_port=build_prescription_facade(session),
        visit_query_port=build_visit_facade(session),
        clinical_note_query_port=build_clinical_note_facade(session),
        soap_note_query_port=build_soap_note_facade(session),
        lab_result_query_port=build_lab_result_facade(session),
        timeline_query_port=build_timeline_facade(session),
    )

    ai_gateway = get_ai_gateway_facade()
    prompt_builder = PromptBuilder(ai_gateway=ai_gateway)
    default_model = resolve_default_ai_model(get_settings())

    service = ClinicalCopilotService(
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        ai_gateway=ai_gateway,
        output_parser=get_output_parser(),
        response_validator=get_response_validator(),
        audit_logger=get_copilot_audit_logger(),
        cost_estimator=get_cost_estimator(),
        default_model=default_model,
    )
    execute_use_case = ExecuteCopilotRequest(service=service)
    return ClinicalCopilotFacade(execute_use_case=execute_use_case)
