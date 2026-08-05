"""Unit tests for `DefaultRiskStratificationAnalysisPromptBuilder`."""

from app.modules.ai.public.dto import AIMessageRole
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskStratificationTemplateSet,
)
from app.modules.risk_stratification_ai.infrastructure.prompts.prompt_builder import (
    DefaultRiskStratificationAnalysisPromptBuilder,
)
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    FakeAIGateway,
    make_input,
    make_lab_value,
    make_vital_signs,
)

_TEMPLATE_SET = RiskStratificationTemplateSet(
    system_template_name="risk_stratification.outpatient.system",
    developer_template_name="risk_stratification.outpatient.developer",
    user_template_name="risk_stratification.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(make_input())

        assert variables["patient_age"] == "Not provided."
        assert variables["lab_values"] == "Not provided."
        assert variables["laboratory_interpretation"] == "Not provided."
        assert variables["radiology_interpretation"] == "Not provided."
        assert variables["pathology_interpretation"] == "Not provided."
        assert variables["medical_reasoning_context"] == "Not provided."

    def test_formats_full_vital_signs(self) -> None:
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            make_input(
                vital_signs=make_vital_signs(
                    respiratory_rate=24,
                    oxygen_saturation=91.0,
                    on_supplemental_oxygen=True,
                    temperature_celsius=38.5,
                    systolic_bp=90,
                    diastolic_bp=60,
                    heart_rate=120,
                )
            )
        )

        vital_signs_text = variables["vital_signs"]
        assert "RR 24/min" in vital_signs_text
        assert "SpO2 91%" in vital_signs_text
        assert "on supplemental oxygen" in vital_signs_text
        assert "Temp 38.5C" in vital_signs_text
        assert "BP 90/60 mmHg" in vital_signs_text
        assert "HR 120/min" in vital_signs_text

    def test_empty_vital_signs_field_uses_not_provided(self) -> None:
        from app.modules.risk_stratification_ai.domain.value_objects import VitalSigns
        from app.modules.risk_stratification_ai.infrastructure.prompts.prompt_builder import (
            _format_vital_signs,
        )

        assert _format_vital_signs(VitalSigns(respiratory_rate=16)) == "RR 16/min"

    def test_formats_lab_values(self) -> None:
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            make_input(lab_values=(make_lab_value(test_name="Creatinine", numeric_value=1.5),))
        )

        assert "Creatinine" in variables["lab_values"]
        assert "1.5" in variables["lab_values"]

    def test_joins_medical_history_and_diagnoses_with_commas(self) -> None:
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            make_input(
                medical_history=("COPD", "Hypertension"),
                diagnoses=("Sepsis", "AKI"),
            )
        )

        assert variables["medical_history"] == "COPD, Hypertension"
        assert variables["diagnoses"] == "Sepsis, AKI"

    def test_carries_through_language(self) -> None:
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(make_input(language="es"))

        assert variables["language"] == "es"

    def test_formats_patient_age(self) -> None:
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(make_input(patient_age=67))

        assert variables["patient_age"] == "67"

    def test_carries_through_peer_module_interpretation_text(self) -> None:
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            make_input(
                laboratory_interpretation="Elevated creatinine consistent with AKI.",
                radiology_interpretation="No acute findings.",
                pathology_interpretation="Benign.",
                medical_reasoning_context="Working diagnosis: sepsis.",
            )
        )

        assert variables["laboratory_interpretation"] == "Elevated creatinine consistent with AKI."
        assert variables["radiology_interpretation"] == "No acute findings."
        assert variables["pathology_interpretation"] == "Benign."
        assert variables["medical_reasoning_context"] == "Working diagnosis: sepsis."


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "risk_stratification.outpatient.system": "system text",
                "risk_stratification.outpatient.developer": "developer text",
                "risk_stratification.outpatient.user": "user text",
            }
        )
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(make_input(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultRiskStratificationAnalysisPromptBuilder(ai_gateway=gateway)
        template_set = RiskStratificationTemplateSet(
            system_template_name="risk_stratification.icu.system",
            developer_template_name="risk_stratification.icu.developer",
            user_template_name="risk_stratification.icu.user",
            version=7,
        )

        await builder.build_messages(make_input(), template_set)

        assert gateway.rendered_calls == [
            ("risk_stratification.icu.system", 7),
            ("risk_stratification.icu.developer", 7),
            ("risk_stratification.icu.user", 7),
        ]
