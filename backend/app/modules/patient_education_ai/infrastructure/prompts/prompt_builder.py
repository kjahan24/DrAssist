"""`DefaultPatientEducationAnalysisPromptBuilder` — the one concrete
`PatientEducationAnalysisPromptBuilderPort` implementation this task
ships: renders a `PatientEducationTemplateSet`'s three templates via AI
Foundation's public `AIGatewayPort.render_prompt`, turning
`PatientEducationInput`'s fields into the flat string `PromptVariables`
the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.patient_education_ai.application.ports import (
    PatientEducationAnalysisPromptBuilderPort,
)
from app.modules.patient_education_ai.domain.value_objects import (
    PatientEducationInput,
    PatientEducationTemplateSet,
)

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


class DefaultPatientEducationAnalysisPromptBuilder(PatientEducationAnalysisPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, input_dto: PatientEducationInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": input_dto.language,
                "patient_age": str(input_dto.patient_age)
                if input_dto.patient_age is not None
                else _NOT_PROVIDED,
                "diagnoses": _join_or_default(input_dto.diagnoses),
                "current_medications": _join_or_default(input_dto.current_medications),
                "clinical_notes": _join_or_default(input_dto.clinical_notes),
                "soap_notes": _join_or_default(input_dto.soap_notes),
                "prescription_ai_output": input_dto.prescription_ai_output or _NOT_PROVIDED,
                "drug_interaction_ai_output": input_dto.drug_interaction_ai_output or _NOT_PROVIDED,
                "risk_stratification_ai_output": input_dto.risk_stratification_ai_output
                or _NOT_PROVIDED,
                "laboratory_interpretation": input_dto.laboratory_interpretation or _NOT_PROVIDED,
                "radiology_interpretation": input_dto.radiology_interpretation or _NOT_PROVIDED,
                "pathology_interpretation": input_dto.pathology_interpretation or _NOT_PROVIDED,
                "medical_reasoning_context": input_dto.medical_reasoning_context or _NOT_PROVIDED,
                "differential_diagnosis_context": input_dto.differential_diagnosis_context
                or _NOT_PROVIDED,
            }
        )

    async def build_messages(
        self,
        input_dto: PatientEducationInput,
        template_set: PatientEducationTemplateSet,
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
