"""Unit tests for `DefaultDrugSafetyAnalysisPromptBuilder`."""

from uuid import uuid4

from app.modules.ai.public.dto import AIMessageRole
from app.modules.drug_interaction_ai.domain.enums import DrugInteractionSetting
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionTemplateSet,
)
from app.modules.drug_interaction_ai.infrastructure.prompts.prompt_builder import (
    DefaultDrugSafetyAnalysisPromptBuilder,
)
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    FakeAIGateway,
    make_medication,
)


def _input(**overrides: object) -> DrugInteractionAnalysisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "medication_setting": DrugInteractionSetting.OUTPATIENT,
        "current_medications": (make_medication(),),
    }
    defaults.update(overrides)
    return DrugInteractionAnalysisInput(**defaults)  # type: ignore[arg-type]


_TEMPLATE_SET = DrugInteractionTemplateSet(
    system_template_name="drug_interaction.outpatient.system",
    developer_template_name="drug_interaction.outpatient.developer",
    user_template_name="drug_interaction.outpatient.user",
    version=1,
)


class TestBuildVariables:
    def test_uses_default_placeholder_text_for_missing_optional_fields(self) -> None:
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input())

        assert variables["new_prescription"] == "Not provided."
        assert variables["diagnosis"] == "Not provided."
        assert variables["patient_age"] == "Not provided."
        assert variables["patient_weight_kg"] == "Not provided."
        assert variables["renal_function"] == "Not provided."
        assert variables["hepatic_function"] == "Not provided."

    def test_formats_current_medications(self) -> None:
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(
                current_medications=(
                    make_medication(
                        drug_name="Warfarin",
                        generic_name="warfarin sodium",
                        dose="5mg",
                        route="oral",
                        frequency="once daily",
                        duration="30 days",
                    ),
                )
            )
        )

        assert "Warfarin" in variables["current_medications"]
        assert "5mg" in variables["current_medications"]
        assert "oral" in variables["current_medications"]

    def test_formats_new_prescription(self) -> None:
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(new_prescription=make_medication(drug_name="Ibuprofen", dose="400mg"))
        )

        assert "Ibuprofen" in variables["new_prescription"]
        assert "400mg" in variables["new_prescription"]

    def test_formats_pregnancy_and_lactation_status_from_enum_values(self) -> None:
        from app.modules.drug_interaction_ai.domain.enums import LactationStatus, PregnancyStatus

        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(
                pregnancy_status=PregnancyStatus.PREGNANT,
                lactation_status=LactationStatus.LACTATING,
            )
        )

        assert variables["pregnancy_status"] == "pregnant"
        assert variables["lactation_status"] == "lactating"

    def test_joins_allergies_and_problem_list_with_commas(self) -> None:
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(
            _input(allergies=("Penicillin", "Sulfa"), problem_list=("Hypertension", "T2DM"))
        )

        assert variables["allergies"] == "Penicillin, Sulfa"
        assert variables["problem_list"] == "Hypertension, T2DM"

    def test_carries_through_language(self) -> None:
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(language="es"))

        assert variables["language"] == "es"

    def test_formats_patient_age_and_weight(self) -> None:
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=FakeAIGateway())

        variables = builder.build_variables(_input(patient_age=45, patient_weight_kg=70.5))

        assert variables["patient_age"] == "45"
        assert variables["patient_weight_kg"] == "70.5"


class TestBuildMessages:
    async def test_renders_three_messages_system_system_user(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "drug_interaction.outpatient.system": "system text",
                "drug_interaction.outpatient.developer": "developer text",
                "drug_interaction.outpatient.user": "user text",
            }
        )
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=gateway)

        messages = await builder.build_messages(_input(), _TEMPLATE_SET)

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_using_the_pinned_template_version(self) -> None:
        gateway = FakeAIGateway()
        builder = DefaultDrugSafetyAnalysisPromptBuilder(ai_gateway=gateway)
        template_set = DrugInteractionTemplateSet(
            system_template_name="drug_interaction.icu.system",
            developer_template_name="drug_interaction.icu.developer",
            user_template_name="drug_interaction.icu.user",
            version=7,
        )

        await builder.build_messages(_input(), template_set)

        assert gateway.rendered_calls == [
            ("drug_interaction.icu.system", 7),
            ("drug_interaction.icu.developer", 7),
            ("drug_interaction.icu.user", 7),
        ]
