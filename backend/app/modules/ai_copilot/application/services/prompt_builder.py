"""`PromptBuilder` — turns a `ClinicalContext` into `PromptVariables`, and
turns a `request_type`/`prompt_version`/`PromptVariables` triple into the
`system`/`developer`/`user` message list AI Foundation's
`ChatCompletionRequest.messages` expects.

Renders three independently-versioned templates —
`"{request_type}.system"`, `"{request_type}.developer"`,
`"{request_type}.user"` — via `AIGatewayPort.render_prompt` (AI
Foundation's public surface; rule 4 of this task: "No direct provider
calls... Everything must go through AIProvider"). Both `system` and
`developer` render to `AIMessageRole.SYSTEM` messages, not a new
"developer" role — AI Foundation's `AIMessageRole` enum
(`app.modules.ai.public.dto`) has no such value and this task forbids
modifying that already-completed module; every provider adapter already
handles multiple system-role messages correctly (e.g.
`ClaudeProvider._split_system_prompt` joins them), so two `SYSTEM`
messages achieves the same "platform instructions, then app-specific
instructions" layering without needing a new role.

All three templates are required for a given `request_type` — there is no
silent "developer prompt is optional" fallback; if one isn't registered,
`AIGatewayPort.render_prompt` raises (an AI Foundation error this module
does not catch — see `domain/exceptions.py`'s module docstring), which is
the correct signal that the request type isn't fully configured yet.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.ai_copilot.application.dto import ClinicalContext


def _join_or_default(items: list[str], *, empty_message: str) -> str:
    return "; ".join(items) if items else empty_message


class PromptBuilder:
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(
        self, context: ClinicalContext, *, extra: dict[str, str] | None = None
    ) -> PromptVariables:
        values: dict[str, str] = {
            "patient_name": f"{context.patient.first_name} {context.patient.last_name}",
            "patient_gender": context.patient.gender.value,
            "patient_date_of_birth": context.patient.date_of_birth.isoformat(),
            "allergies_summary": self._summarize_allergies(context),
            "medications_summary": self._summarize_medications(context),
            "conditions_summary": self._summarize_conditions(context),
            "visits_summary": self._summarize_visits(context),
            "clinical_notes_summary": self._summarize_clinical_notes(context),
            "soap_notes_summary": self._summarize_soap_notes(context),
            "lab_results_summary": self._summarize_lab_results(context),
            "timeline_summary": self._summarize_timeline(context),
        }
        if extra:
            values.update(extra)
        return PromptVariables(values)

    async def build_messages(
        self, *, request_type: str, prompt_version: int, variables: PromptVariables
    ) -> list[AIMessage]:
        system_text = await self._ai_gateway.render_prompt(
            f"{request_type}.system", variables, version=prompt_version
        )
        developer_text = await self._ai_gateway.render_prompt(
            f"{request_type}.developer", variables, version=prompt_version
        )
        user_text = await self._ai_gateway.render_prompt(
            f"{request_type}.user", variables, version=prompt_version
        )
        return [
            AIMessage(role=AIMessageRole.SYSTEM, content=system_text),
            AIMessage(role=AIMessageRole.SYSTEM, content=developer_text),
            AIMessage(role=AIMessageRole.USER, content=user_text),
        ]

    def _summarize_allergies(self, context: ClinicalContext) -> str:
        items = [f"{a.allergen_name} ({a.severity.value})" for a in context.allergies]
        return _join_or_default(items, empty_message="No known allergies.")

    def _summarize_medications(self, context: ClinicalContext) -> str:
        items = [
            f"{item.medication_name} {item.dosage}"
            for prescription in context.medications
            for item in prescription.items
        ]
        return _join_or_default(items, empty_message="No current medications.")

    def _summarize_conditions(self, context: ClinicalContext) -> str:
        items = [f"{c.condition_name} ({c.status.value})" for c in context.conditions]
        return _join_or_default(items, empty_message="No known medical conditions.")

    def _summarize_visits(self, context: ClinicalContext) -> str:
        items = [
            f"{v.visit_date.isoformat() if v.visit_date else 'undated'}: "
            f"{v.reason_for_visit or v.chief_complaint_summary or 'visit'}"
            for v in context.visits
        ]
        return _join_or_default(items, empty_message="No prior visits on record.")

    def _summarize_clinical_notes(self, context: ClinicalContext) -> str:
        items = [
            f"{n.encounter_datetime.isoformat()}: {n.assessment_summary or n.note_type.value}"
            for n in context.clinical_notes
        ]
        return _join_or_default(items, empty_message="No prior clinical notes on record.")

    def _summarize_soap_notes(self, context: ClinicalContext) -> str:
        items = [s.assessment for s in context.soap_notes if s.assessment]
        return _join_or_default(items, empty_message="No prior SOAP notes on record.")

    def _summarize_lab_results(self, context: ClinicalContext) -> str:
        items = [
            f"{result.reported_at.isoformat()}: "
            f"{', '.join(item.test_name for item in result.items) or 'lab result'}"
            for result in context.lab_results
        ]
        return _join_or_default(items, empty_message="No prior lab results on record.")

    def _summarize_timeline(self, context: ClinicalContext) -> str:
        items = [
            f"{event.event_datetime.isoformat()}: {event.title}"
            for event in context.timeline_events
        ]
        return _join_or_default(items, empty_message="No timeline events on record.")
