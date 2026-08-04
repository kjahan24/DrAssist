"""`DefaultICD10PromptBuilder` — the one concrete `ICD10PromptBuilderPort`
implementation this task ships: renders an `ICD10TemplateSet`'s three
templates via AI Foundation's public `AIGatewayPort.render_prompt`,
turning `ICD10CodingInput`'s fields into the flat string `PromptVariables`
the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.icd10_ai.application.ports import ICD10PromptBuilderPort
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput, ICD10TemplateSet

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _text_or_default(value: str | None) -> str:
    return value.strip() if value and value.strip() else _NOT_PROVIDED


class DefaultICD10PromptBuilder(ICD10PromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, coding_input: ICD10CodingInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": coding_input.language,
                "patient_age": str(coding_input.patient_age)
                if coding_input.patient_age is not None
                else _NOT_PROVIDED,
                "patient_sex": coding_input.patient_sex.value
                if coding_input.patient_sex is not None
                else _NOT_PROVIDED,
                "visit_context": _text_or_default(coding_input.visit_context),
                "chief_complaint": coding_input.chief_complaint,
                "history_of_present_illness": _text_or_default(
                    coding_input.history_of_present_illness
                ),
                "symptoms": _join_or_default(coding_input.symptoms),
                "review_of_systems": _text_or_default(coding_input.review_of_systems),
                "physical_examination": _text_or_default(coding_input.physical_examination),
                "assessment": _text_or_default(coding_input.assessment),
                "plan": _text_or_default(coding_input.plan),
                "clinical_note": _text_or_default(coding_input.clinical_note),
                "soap_note": _text_or_default(coding_input.soap_note),
                "existing_diagnoses": _join_or_default(coding_input.existing_diagnoses),
            }
        )

    async def build_messages(
        self, coding_input: ICD10CodingInput, template_set: ICD10TemplateSet
    ) -> list[AIMessage]:
        variables = self.build_variables(coding_input)
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
