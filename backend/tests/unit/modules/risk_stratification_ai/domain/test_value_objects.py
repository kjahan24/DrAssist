"""Tests for the AI Risk Stratification & Early Warning Score module's
domain value objects — construction, `__post_init__` validation, and
computed properties."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.risk_stratification_ai.domain.enums import (
    ConsciousnessLevel,
    OverallRiskLevel,
    RiskAnalysisStatus,
    RiskCategory,
    RiskStratificationOutputFormat,
    RiskStratificationSetting,
)
from app.modules.risk_stratification_ai.domain.exceptions import (
    IncompleteLaboratoryValueError,
    InvalidRiskStratificationInputError,
    MissingVitalSignsError,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    GenerationSession,
    LabValue,
    RiskScore,
    RiskStratificationInput,
    RiskStratificationResult,
    RiskStratificationStreamChunk,
    RiskStratificationTemplateSet,
    VitalSigns,
)


class TestVitalSigns:
    def test_all_fields_none_is_empty(self) -> None:
        assert VitalSigns().is_empty is True

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"respiratory_rate": 16},
            {"oxygen_saturation": 97.0},
            {"on_supplemental_oxygen": False},
            {"temperature_celsius": 37.0},
            {"systolic_bp": 120},
            {"diastolic_bp": 80},
            {"heart_rate": 78},
            {"consciousness_level": ConsciousnessLevel.ALERT},
        ],
    )
    def test_any_single_field_makes_it_not_empty(self, kwargs: dict[str, object]) -> None:
        assert VitalSigns(**kwargs).is_empty is False  # type: ignore[arg-type]

    def test_valid_full_construction(self) -> None:
        vital_signs = VitalSigns(
            respiratory_rate=16,
            oxygen_saturation=97.0,
            on_supplemental_oxygen=False,
            temperature_celsius=37.0,
            systolic_bp=120,
            diastolic_bp=80,
            heart_rate=78,
            consciousness_level=ConsciousnessLevel.ALERT,
        )
        assert vital_signs.respiratory_rate == 16
        assert vital_signs.is_empty is False

    @pytest.mark.parametrize("respiratory_rate", [-1, 101])
    def test_out_of_range_respiratory_rate_raises(self, respiratory_rate: int) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            VitalSigns(respiratory_rate=respiratory_rate)

    @pytest.mark.parametrize("respiratory_rate", [0, 100])
    def test_boundary_respiratory_rate_is_valid(self, respiratory_rate: int) -> None:
        assert VitalSigns(respiratory_rate=respiratory_rate).respiratory_rate == respiratory_rate

    @pytest.mark.parametrize("oxygen_saturation", [-0.1, 100.1])
    def test_out_of_range_oxygen_saturation_raises(self, oxygen_saturation: float) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            VitalSigns(oxygen_saturation=oxygen_saturation)

    @pytest.mark.parametrize("oxygen_saturation", [0.0, 100.0])
    def test_boundary_oxygen_saturation_is_valid(self, oxygen_saturation: float) -> None:
        vital_signs = VitalSigns(oxygen_saturation=oxygen_saturation)
        assert vital_signs.oxygen_saturation == oxygen_saturation

    @pytest.mark.parametrize("temperature_celsius", [24.9, 45.1])
    def test_out_of_range_temperature_raises(self, temperature_celsius: float) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            VitalSigns(temperature_celsius=temperature_celsius)

    @pytest.mark.parametrize("temperature_celsius", [25.0, 45.0])
    def test_boundary_temperature_is_valid(self, temperature_celsius: float) -> None:
        vital_signs = VitalSigns(temperature_celsius=temperature_celsius)
        assert vital_signs.temperature_celsius == temperature_celsius

    def test_negative_systolic_bp_raises(self) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            VitalSigns(systolic_bp=-1)

    def test_zero_systolic_bp_is_valid(self) -> None:
        assert VitalSigns(systolic_bp=0).systolic_bp == 0

    def test_negative_diastolic_bp_raises(self) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            VitalSigns(diastolic_bp=-1)

    @pytest.mark.parametrize("heart_rate", [-1, 301])
    def test_out_of_range_heart_rate_raises(self, heart_rate: int) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            VitalSigns(heart_rate=heart_rate)

    @pytest.mark.parametrize("heart_rate", [0, 300])
    def test_boundary_heart_rate_is_valid(self, heart_rate: int) -> None:
        assert VitalSigns(heart_rate=heart_rate).heart_rate == heart_rate


class TestLabValue:
    def test_valid_with_value_only(self) -> None:
        lab = LabValue(test_name="Creatinine", value="1.2 mg/dL")
        assert lab.test_name == "Creatinine"

    def test_valid_with_numeric_value_only(self) -> None:
        lab = LabValue(test_name="Creatinine", numeric_value=1.2)
        assert lab.numeric_value == 1.2

    def test_valid_with_both(self) -> None:
        lab = LabValue(test_name="Creatinine", value="1.2 mg/dL", numeric_value=1.2)
        assert lab.value == "1.2 mg/dL"
        assert lab.numeric_value == 1.2

    def test_blank_test_name_raises_generic_input_error(self) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            LabValue(test_name="", numeric_value=1.2)

    def test_whitespace_only_test_name_raises(self) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            LabValue(test_name="   ", numeric_value=1.2)

    def test_missing_value_and_numeric_value_raises_incomplete_error(self) -> None:
        with pytest.raises(IncompleteLaboratoryValueError):
            LabValue(test_name="Creatinine")

    def test_blank_value_and_no_numeric_value_raises_incomplete_error(self) -> None:
        with pytest.raises(IncompleteLaboratoryValueError):
            LabValue(test_name="Creatinine", value="   ")


class TestRiskStratificationInput:
    def _vital_signs(self) -> VitalSigns:
        return VitalSigns(respiratory_rate=16)

    def test_valid_minimal_construction(self) -> None:
        input_dto = RiskStratificationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            risk_setting=RiskStratificationSetting.OUTPATIENT,
            vital_signs=self._vital_signs(),
        )
        assert input_dto.language == "en"
        assert input_dto.output_format is RiskStratificationOutputFormat.JSON
        assert input_dto.lab_values == ()
        assert input_dto.laboratory_interpretation is None

    def test_empty_vital_signs_raises_missing_vital_signs_error(self) -> None:
        with pytest.raises(MissingVitalSignsError):
            RiskStratificationInput(
                organization_id=uuid4(),
                patient_id=uuid4(),
                risk_setting=RiskStratificationSetting.OUTPATIENT,
                vital_signs=VitalSigns(),
            )

    def test_blank_language_raises(self) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            RiskStratificationInput(
                organization_id=uuid4(),
                patient_id=uuid4(),
                risk_setting=RiskStratificationSetting.OUTPATIENT,
                vital_signs=self._vital_signs(),
                language="   ",
            )

    @pytest.mark.parametrize("patient_age", [-1, 151])
    def test_out_of_range_patient_age_raises(self, patient_age: int) -> None:
        with pytest.raises(InvalidRiskStratificationInputError):
            RiskStratificationInput(
                organization_id=uuid4(),
                patient_id=uuid4(),
                risk_setting=RiskStratificationSetting.OUTPATIENT,
                vital_signs=self._vital_signs(),
                patient_age=patient_age,
            )

    @pytest.mark.parametrize("patient_age", [0, 150])
    def test_boundary_patient_age_is_valid(self, patient_age: int) -> None:
        input_dto = RiskStratificationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            risk_setting=RiskStratificationSetting.OUTPATIENT,
            vital_signs=self._vital_signs(),
            patient_age=patient_age,
        )
        assert input_dto.patient_age == patient_age

    def test_patient_age_none_is_valid(self) -> None:
        input_dto = RiskStratificationInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            risk_setting=RiskStratificationSetting.OUTPATIENT,
            vital_signs=self._vital_signs(),
        )
        assert input_dto.patient_age is None


class TestRiskScore:
    def test_construction(self) -> None:
        score = RiskScore(
            category=RiskCategory.NEWS2,
            score_value=3.0,
            contributing_factors=("Respiratory rate 22/min",),
            clinical_explanation="NEWS2 score of 3.",
        )
        assert score.category is RiskCategory.NEWS2
        assert score.score_value == 3.0
        assert score.contributing_factors == ("Respiratory rate 22/min",)

    def test_score_value_may_be_none(self) -> None:
        score = RiskScore(
            category=RiskCategory.SEPSIS_RISK,
            score_value=None,
            contributing_factors=(),
            clinical_explanation="Sepsis risk factors identified.",
        )
        assert score.score_value is None


class TestRiskStratificationResult:
    def _base_kwargs(self) -> dict[str, object]:
        return {
            "overall_risk_level": OverallRiskLevel.LOW,
            "risk_scores": (),
            "early_warning_indicators": (),
            "recommended_monitoring": (),
            "suggested_escalation": (),
            "suggested_follow_up": (),
            "red_flag_alerts": (),
            "clinical_reasoning": "",
            "confidence_score": None,
            "raw_text": "{}",
            "output_format": RiskStratificationOutputFormat.JSON,
        }

    def test_fully_empty_result_is_empty(self) -> None:
        result = RiskStratificationResult(**self._base_kwargs())  # type: ignore[arg-type]
        assert result.is_empty is True

    def test_non_empty_risk_scores_is_not_empty(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["risk_scores"] = (
            RiskScore(
                category=RiskCategory.NEWS2,
                score_value=1.0,
                contributing_factors=(),
                clinical_explanation="",
            ),
        )
        result = RiskStratificationResult(**kwargs)  # type: ignore[arg-type]
        assert result.is_empty is False

    @pytest.mark.parametrize(
        "field_name",
        [
            "early_warning_indicators",
            "recommended_monitoring",
            "suggested_escalation",
            "suggested_follow_up",
            "red_flag_alerts",
        ],
    )
    def test_non_empty_list_field_is_not_empty(self, field_name: str) -> None:
        kwargs = self._base_kwargs()
        kwargs[field_name] = ("something",)
        result = RiskStratificationResult(**kwargs)  # type: ignore[arg-type]
        assert result.is_empty is False

    def test_non_blank_clinical_reasoning_is_not_empty(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["clinical_reasoning"] = "Grounded in vital signs."
        result = RiskStratificationResult(**kwargs)  # type: ignore[arg-type]
        assert result.is_empty is False

    def test_whitespace_only_clinical_reasoning_is_still_empty(self) -> None:
        kwargs = self._base_kwargs()
        kwargs["clinical_reasoning"] = "   "
        result = RiskStratificationResult(**kwargs)  # type: ignore[arg-type]
        assert result.is_empty is True


class TestRiskStratificationTemplateSet:
    def test_construction(self) -> None:
        template_set = RiskStratificationTemplateSet(
            system_template_name="risk_stratification.outpatient.system",
            developer_template_name="risk_stratification.outpatient.developer",
            user_template_name="risk_stratification.outpatient.user",
            version=1,
        )
        assert template_set.version == 1


class TestGenerationSession:
    def test_construction_with_defaults(self) -> None:
        session = GenerationSession(
            generation_id=uuid4(),
            provider="mock",
            model="mock-model",
            risk_setting="outpatient",
            language="en",
            status=RiskAnalysisStatus.COMPLETED,
        )
        assert session.latency_ms == 0.0
        assert session.prompt_tokens == 0
        assert session.completion_tokens == 0
        assert session.total_tokens == 0
        assert session.estimated_cost_usd == 0.0
        assert isinstance(session.created_at, datetime)
        assert session.created_at.tzinfo is UTC

    def test_status_failed(self) -> None:
        session = GenerationSession(
            generation_id=uuid4(),
            provider="mock",
            model="mock-model",
            risk_setting="outpatient",
            language="en",
            status=RiskAnalysisStatus.FAILED,
        )
        assert session.status is RiskAnalysisStatus.FAILED


class TestRiskStratificationStreamChunk:
    def test_default_is_final_false(self) -> None:
        chunk = RiskStratificationStreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_is_final_true(self) -> None:
        chunk = RiskStratificationStreamChunk(delta="", is_final=True)
        assert chunk.is_final is True
