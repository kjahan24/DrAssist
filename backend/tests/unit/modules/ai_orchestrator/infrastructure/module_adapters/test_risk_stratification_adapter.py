"""Unit tests for `RiskStratificationWorkflowAdapter` and its module-level
`parse_vital_signs` helper — the most complex adapter in this package,
since it best-effort-parses a generic `Mapping[str, str]` into that peer
module's own typed `VitalSigns` value object."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.risk_stratification_adapter import (
    RiskStratificationWorkflowAdapter,
    parse_vital_signs,
)
from app.modules.risk_stratification_ai.public.dto import ConsciousnessLevel
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeRiskStratificationAIPort,
    make_generated_risk_stratification,
)


class TestParseVitalSigns:
    def test_empty_mapping_produces_empty_vital_signs(self) -> None:
        assert parse_vital_signs({}).is_empty

    def test_recognizes_canonical_key_names(self) -> None:
        vitals = parse_vital_signs(
            {
                "respiratory_rate": "22",
                "oxygen_saturation": "94",
                "temperature_celsius": "38.5",
                "systolic_bp": "100",
                "diastolic_bp": "60",
                "heart_rate": "110",
            }
        )

        assert vitals.respiratory_rate == 22
        assert vitals.oxygen_saturation == 94.0
        assert vitals.temperature_celsius == 38.5
        assert vitals.systolic_bp == 100
        assert vitals.diastolic_bp == 60
        assert vitals.heart_rate == 110

    def test_recognizes_alias_key_names_case_insensitively(self) -> None:
        vitals = parse_vital_signs(
            {"RR": "18", "SpO2": "97", "HR": "80", "SBP": "120", "DBP": "80"}
        )

        assert vitals.respiratory_rate == 18
        assert vitals.oxygen_saturation == 97.0
        assert vitals.heart_rate == 80
        assert vitals.systolic_bp == 120
        assert vitals.diastolic_bp == 80

    def test_parses_supplemental_oxygen_boolean(self) -> None:
        assert parse_vital_signs({"on_supplemental_oxygen": "true"}).on_supplemental_oxygen is True
        assert parse_vital_signs({"supplemental_oxygen": "no"}).on_supplemental_oxygen is False

    def test_parses_consciousness_level(self) -> None:
        vitals = parse_vital_signs({"consciousness_level": "alert"})
        assert vitals.consciousness_level == ConsciousnessLevel.ALERT

    def test_unrecognized_keys_are_silently_skipped(self) -> None:
        assert parse_vital_signs({"weight_kg": "70"}).is_empty

    def test_unparseable_numeric_value_is_silently_skipped_not_raised(self) -> None:
        vitals = parse_vital_signs({"heart_rate": "not-a-number"})
        assert vitals.heart_rate is None
        assert vitals.is_empty

    def test_unparseable_consciousness_level_is_silently_skipped(self) -> None:
        vitals = parse_vital_signs({"consciousness_level": "not-a-real-level"})
        assert vitals.consciousness_level is None


class TestRiskStratificationWorkflowAdapter:
    def test_module_is_risk_stratification(self) -> None:
        adapter = RiskStratificationWorkflowAdapter(facade=FakeRiskStratificationAIPort())
        assert adapter.module == WorkflowModule.RISK_STRATIFICATION

    def test_check_prerequisites_missing_when_no_parseable_vitals(self) -> None:
        adapter = RiskStratificationWorkflowAdapter(facade=FakeRiskStratificationAIPort())
        reasons = adapter.check_prerequisites(make_bundle())
        assert reasons == ("no parseable vital signs were provided",)

    def test_check_prerequisites_ready_when_at_least_one_vital_present(self) -> None:
        adapter = RiskStratificationWorkflowAdapter(facade=FakeRiskStratificationAIPort())
        bundle = make_bundle(vital_signs={"heart_rate": "80"})
        assert adapter.check_prerequisites(bundle) == ()

    async def test_execute_synthesizes_lab_values_from_free_text_findings(self) -> None:
        facade = FakeRiskStratificationAIPort()
        adapter = RiskStratificationWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            vital_signs={"heart_rate": "80"}, laboratory_findings=("lactate elevated",)
        )

        await adapter.execute(bundle, {})

        lab_values = facade.received[0].lab_values
        assert len(lab_values) == 1
        assert lab_values[0].test_name == "Finding 1"
        assert lab_values[0].value == "lactate elevated"

    async def test_execute_chains_upstream_lab_radiology_pathology_and_reasoning(self) -> None:
        facade = FakeRiskStratificationAIPort()
        adapter = RiskStratificationWorkflowAdapter(facade=facade)
        bundle = make_bundle(vital_signs={"heart_rate": "80"})
        context = {
            WorkflowModule.LAB_INTERPRETATION: "upstream lab",
            WorkflowModule.RADIOLOGY_INTERPRETATION: "upstream radiology",
            WorkflowModule.PATHOLOGY_INTERPRETATION: "upstream pathology",
            WorkflowModule.MEDICAL_REASONING: "upstream reasoning",
        }

        await adapter.execute(bundle, context)

        input_dto = facade.received[0]
        assert input_dto.laboratory_interpretation == "upstream lab"
        assert input_dto.radiology_interpretation == "upstream radiology"
        assert input_dto.pathology_interpretation == "upstream pathology"
        assert input_dto.medical_reasoning_context == "upstream reasoning"

    async def test_execute_returns_completed_step_result_with_confidence(self) -> None:
        facade = FakeRiskStratificationAIPort(
            generated=make_generated_risk_stratification(
                raw_text="the risk stratification", confidence_score=0.6
            )
        )
        adapter = RiskStratificationWorkflowAdapter(facade=facade)
        bundle = make_bundle(vital_signs={"heart_rate": "80"})

        result = await adapter.execute(bundle, {})

        assert result.module == WorkflowModule.RISK_STRATIFICATION
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the risk stratification"
        assert result.confidence_score == 0.6

    async def test_execute_passes_patient_age_and_diagnoses_through(self) -> None:
        facade = FakeRiskStratificationAIPort()
        adapter = RiskStratificationWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            vital_signs={"heart_rate": "80"}, patient_age=77, diagnoses=("sepsis",)
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.patient_age == 77
        assert input_dto.diagnoses == ("sepsis",)
        assert input_dto.medical_history == ("sepsis",)
