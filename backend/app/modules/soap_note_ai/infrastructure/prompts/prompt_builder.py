"""`DefaultSOAPPromptBuilder` — the one concrete `SOAPPromptBuilderPort`
implementation this task ships: renders a `SOAPTemplateSet`'s three
templates via AI Foundation's public `AIGatewayPort.render_prompt`,
turning `SOAPEncounterInput`'s fields into the flat string
`PromptVariables` the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.soap_note_ai.application.ports import SOAPPromptBuilderPort
from app.modules.soap_note_ai.domain.value_objects import SOAPEncounterInput, SOAPTemplateSet

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _text_or_default(value: str | None) -> str:
    return value.strip() if value and value.strip() else _NOT_PROVIDED


def _format_vitals(vitals: dict[str, str]) -> str:
    if not vitals:
        return _NOT_PROVIDED
    return ", ".join(f"{key}: {value}" for key, value in vitals.items())


class DefaultSOAPPromptBuilder(SOAPPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, encounter: SOAPEncounterInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": encounter.language,
                "patient_age": str(encounter.patient_age)
                if encounter.patient_age is not None
                else _NOT_PROVIDED,
                "patient_sex": encounter.patient_sex.value
                if encounter.patient_sex is not None
                else _NOT_PROVIDED,
                "visit_type": _text_or_default(encounter.visit_type),
                "chief_complaint": encounter.chief_complaint,
                "history_of_present_illness": _text_or_default(
                    encounter.history_of_present_illness
                ),
                "symptoms": _join_or_default(encounter.symptoms),
                "review_of_systems": _text_or_default(encounter.review_of_systems),
                "physical_examination": _text_or_default(encounter.physical_examination),
                "vitals": _format_vitals(dict(encounter.vitals)),
                "medications": _join_or_default(encounter.medications),
                "allergies": _join_or_default(encounter.allergies),
                "diagnoses": _join_or_default(encounter.diagnoses),
                "assessment": _text_or_default(encounter.assessment),
                "plan": _text_or_default(encounter.plan),
                "clinician_instructions": _text_or_default(encounter.clinician_instructions),
                "encounter_context": _text_or_default(encounter.encounter_context),
            }
        )

    async def build_messages(
        self, encounter: SOAPEncounterInput, template_set: SOAPTemplateSet
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
