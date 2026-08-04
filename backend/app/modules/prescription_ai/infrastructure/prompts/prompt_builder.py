"""`DefaultPrescriptionPromptBuilder` — the one concrete
`PrescriptionPromptBuilderPort` implementation this task ships: renders a
`PrescriptionTemplateSet`'s three templates via AI Foundation's public
`AIGatewayPort.render_prompt`, turning `PrescriptionContextInput`'s
fields into the flat string `PromptVariables` the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.prescription_ai.application.ports import PrescriptionPromptBuilderPort
from app.modules.prescription_ai.domain.value_objects import (
    PrescriptionContextInput,
    PrescriptionTemplateSet,
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


class DefaultPrescriptionPromptBuilder(PrescriptionPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, context: PrescriptionContextInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": context.language,
                "patient_age": str(context.patient_age)
                if context.patient_age is not None
                else _NOT_PROVIDED,
                "patient_sex": context.patient_sex.value
                if context.patient_sex is not None
                else _NOT_PROVIDED,
                "pregnancy_status": context.pregnancy_status.value
                if context.pregnancy_status is not None
                else _NOT_PROVIDED,
                "weight_kg": str(context.weight_kg)
                if context.weight_kg is not None
                else _NOT_PROVIDED,
                "visit_type": _text_or_default(context.visit_type),
                "chief_complaint": context.chief_complaint,
                "history_of_present_illness": _text_or_default(context.history_of_present_illness),
                "symptoms": _join_or_default(context.symptoms),
                "review_of_systems": _text_or_default(context.review_of_systems),
                "physical_examination": _text_or_default(context.physical_examination),
                "vitals": _format_vitals(dict(context.vitals)),
                "assessment": _text_or_default(context.assessment),
                "plan": _text_or_default(context.plan),
                "clinical_note": _text_or_default(context.clinical_note),
                "soap_note": _text_or_default(context.soap_note),
                "icd10_suggestions": _join_or_default(context.icd10_suggestions),
                "existing_medications": _join_or_default(context.existing_medications),
                "allergies": _join_or_default(context.allergies),
                "medical_conditions": _join_or_default(context.medical_conditions),
                "laboratory_results": _join_or_default(context.laboratory_results),
            }
        )

    async def build_messages(
        self, context: PrescriptionContextInput, template_set: PrescriptionTemplateSet
    ) -> list[AIMessage]:
        variables = self.build_variables(context)
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
