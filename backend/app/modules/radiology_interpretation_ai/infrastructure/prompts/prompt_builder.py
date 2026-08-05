"""`DefaultRadiologyPromptBuilder` — the one concrete
`RadiologyPromptBuilderPort` implementation this task ships: renders a
`RadiologyInterpretationTemplateSet`'s three templates via AI
Foundation's public `AIGatewayPort.render_prompt`, turning
`RadiologyInterpretationInput`'s fields into the flat string
`PromptVariables` the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.radiology_interpretation_ai.application.ports import RadiologyPromptBuilderPort
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationInput,
    RadiologyInterpretationTemplateSet,
)

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _text_or_default(value: str | None) -> str:
    return value.strip() if value and value.strip() else _NOT_PROVIDED


class DefaultRadiologyPromptBuilder(RadiologyPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, input_dto: RadiologyInterpretationInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": input_dto.language,
                "examination_type": input_dto.examination_type.value,
                "report_text": input_dto.report_text,
                "patient_age": str(input_dto.patient_age)
                if input_dto.patient_age is not None
                else _NOT_PROVIDED,
                "patient_sex": input_dto.patient_sex.value
                if input_dto.patient_sex is not None
                else _NOT_PROVIDED,
                "pregnancy_status": input_dto.pregnancy_status.value
                if input_dto.pregnancy_status is not None
                else _NOT_PROVIDED,
                "visit_type": _text_or_default(input_dto.visit_type),
                "clinical_notes": _join_or_default(input_dto.clinical_notes),
                "soap_notes": _join_or_default(input_dto.soap_notes),
                "icd10_suggestions": _join_or_default(input_dto.icd10_suggestions),
                "differential_diagnoses": _join_or_default(input_dto.differential_diagnoses),
                "laboratory_interpretation": _text_or_default(input_dto.laboratory_interpretation),
                "medical_reasoning_context": _text_or_default(input_dto.medical_reasoning_context),
            }
        )

    async def build_messages(
        self,
        input_dto: RadiologyInterpretationInput,
        template_set: RadiologyInterpretationTemplateSet,
    ) -> list[AIMessage]:
        variables = self.build_variables(input_dto)
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
