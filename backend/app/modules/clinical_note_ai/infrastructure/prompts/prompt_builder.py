"""`DefaultPromptBuilder` — the one concrete `PromptBuilderPort`
implementation this task ships: renders a `ClinicalNoteTemplateSet`'s
three templates via AI Foundation's public `AIGatewayPort.render_prompt`
(rule 4: "No direct provider calls... Everything must go through
AIProvider"), turning `ClinicalEncounterInput`'s fields into the flat
string `PromptVariables` the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.clinical_note_ai.application.ports import PromptBuilderPort
from app.modules.clinical_note_ai.domain.value_objects import (
    ClinicalEncounterInput,
    ClinicalNoteTemplateSet,
)

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _text_or_default(value: str | None) -> str:
    return value.strip() if value and value.strip() else _NOT_PROVIDED


def _format_vitals(vitals: dict[str, str]) -> str:
    if not vitals:
        return _NOT_PROVIDED
    return ", ".join(f"{key}: {value}" for key, value in vitals.items())


class DefaultPromptBuilder(PromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, encounter: ClinicalEncounterInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": encounter.language,
                "chief_complaint": encounter.chief_complaint,
                "history_of_present_illness": _text_or_default(
                    encounter.history_of_present_illness
                ),
                "symptoms": _join_or_default(encounter.symptoms),
                "observations": _join_or_default(encounter.observations),
                "physical_examination": _text_or_default(encounter.physical_examination),
                "assessment": _text_or_default(encounter.assessment),
                "plan": _text_or_default(encounter.plan),
                "medications": _join_or_default(encounter.medications),
                "allergies": _join_or_default(encounter.allergies),
                "vitals": _format_vitals(dict(encounter.vitals)),
                "diagnoses": _join_or_default(encounter.diagnoses),
                "clinician_instructions": _text_or_default(encounter.clinician_instructions),
                "encounter_context": _text_or_default(encounter.encounter_context),
            }
        )

    async def build_messages(
        self, encounter: ClinicalEncounterInput, template_set: ClinicalNoteTemplateSet
    ) -> list[AIMessage]:
        variables = self.build_variables(encounter)
        system_text = await self._ai_gateway.render_prompt(
            template_set.system_template_name, variables, version=template_set.version
        )
        developer_text = await self._ai_gateway.render_prompt(
            template_set.developer_template_name, variables, version=template_set.version
        )
        user_text = await self._ai_gateway.render_prompt(
            template_set.user_template_name, variables, version=template_set.version
        )
        return [
            AIMessage(role=AIMessageRole.SYSTEM, content=system_text),
            AIMessage(role=AIMessageRole.SYSTEM, content=developer_text),
            AIMessage(role=AIMessageRole.USER, content=user_text),
        ]
