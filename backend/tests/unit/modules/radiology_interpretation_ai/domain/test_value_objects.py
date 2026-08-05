"""Unit tests for the AI Radiology Interpretation module's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyExaminationType,
    RadiologyFindingCategory,
    RadiologyOutputFormat,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    EmptyRadiologyReportError,
    InvalidRadiologyInterpretationInputError,
    MalformedRadiologyReportError,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyFinding,
    RadiologyInterpretationInput,
    RadiologyInterpretationResult,
)


def _input(**overrides: object) -> RadiologyInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "report_text": "The lungs are clear bilaterally. No acute cardiopulmonary abnormality.",
        "examination_type": RadiologyExaminationType.CHEST_XRAY,
        "radiology_setting": RadiologySetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return RadiologyInterpretationInput(**defaults)  # type: ignore[arg-type]


class TestRadiologyInterpretationInput:
    def test_accepts_a_well_formed_input(self) -> None:
        _input()

    def test_raises_when_report_text_is_blank(self) -> None:
        with pytest.raises(EmptyRadiologyReportError):
            _input(report_text="   ")

    def test_raises_when_report_text_is_too_short(self) -> None:
        with pytest.raises(MalformedRadiologyReportError):
            _input(report_text="short")

    def test_raises_when_report_text_has_no_alphabetic_content(self) -> None:
        with pytest.raises(MalformedRadiologyReportError):
            _input(report_text="1234567890!!!!!!")

    def test_accepts_a_report_at_the_minimum_length(self) -> None:
        _input(report_text="No acute findings noted on this study today.")

    def test_raises_when_language_is_blank(self) -> None:
        with pytest.raises(InvalidRadiologyInterpretationInputError):
            _input(language="   ")

    @pytest.mark.parametrize("patient_age", [-1, 151])
    def test_raises_when_patient_age_is_out_of_range(self, patient_age: int) -> None:
        with pytest.raises(InvalidRadiologyInterpretationInputError):
            _input(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 150, 42])
    def test_accepts_boundary_patient_ages(self, patient_age: int) -> None:
        _input(patient_age=patient_age)

    def test_accepts_a_missing_patient_age(self) -> None:
        _input(patient_age=None)

    def test_carries_through_examination_type(self) -> None:
        input_dto = _input(examination_type=RadiologyExaminationType.CT_BRAIN)
        assert input_dto.examination_type is RadiologyExaminationType.CT_BRAIN

    def test_accepts_laboratory_interpretation_and_medical_reasoning_context_as_plain_text(
        self,
    ) -> None:
        input_dto = _input(
            laboratory_interpretation="Potassium critically elevated at 6.8 mmol/L.",
            medical_reasoning_context="High pretest probability of renal failure.",
        )
        assert input_dto.laboratory_interpretation == "Potassium critically elevated at 6.8 mmol/L."
        assert input_dto.medical_reasoning_context == "High pretest probability of renal failure."


class TestRadiologyFinding:
    def test_carries_its_fields(self) -> None:
        finding = RadiologyFinding(
            description="Small pneumothorax",
            category=RadiologyFindingCategory.CRITICAL,
            anatomical_region="Right apex",
        )
        assert finding.category is RadiologyFindingCategory.CRITICAL
        assert finding.anatomical_region == "Right apex"

    def test_anatomical_region_defaults_to_none(self) -> None:
        finding = RadiologyFinding(description="x", category=RadiologyFindingCategory.NORMAL)
        assert finding.anatomical_region is None


class TestRadiologyInterpretationResult:
    def _result(self, **overrides: object) -> RadiologyInterpretationResult:
        defaults: dict[str, object] = {
            "examination_summary": "Findings reviewed.",
            "findings": (
                RadiologyFinding(
                    description="Clear lung fields", category=RadiologyFindingCategory.NORMAL
                ),
                RadiologyFinding(
                    description="Right lower lobe opacity",
                    category=RadiologyFindingCategory.ABNORMAL,
                ),
                RadiologyFinding(
                    description="Small hepatic cyst", category=RadiologyFindingCategory.INCIDENTAL
                ),
                RadiologyFinding(
                    description="Large pneumothorax", category=RadiologyFindingCategory.CRITICAL
                ),
            ),
            "clinical_significance": "Right lower lobe opacity may represent consolidation.",
            "differential_imaging_considerations": (),
            "suggested_follow_up_imaging": (),
            "suggested_specialist_referral": (),
            "red_flag_warnings": (),
            "confidence_score": 0.7,
            "clinical_reasoning": "Grounded in the described opacity and pneumothorax.",
            "raw_text": "{}",
            "output_format": RadiologyOutputFormat.JSON,
        }
        defaults.update(overrides)
        return RadiologyInterpretationResult(**defaults)  # type: ignore[arg-type]

    def test_normal_findings_filters_to_normal_only(self) -> None:
        result = self._result()
        assert [f.description for f in result.normal_findings] == ["Clear lung fields"]

    def test_abnormal_findings_filters_to_abnormal_only(self) -> None:
        result = self._result()
        assert [f.description for f in result.abnormal_findings] == ["Right lower lobe opacity"]

    def test_incidental_findings_filters_to_incidental_only(self) -> None:
        result = self._result()
        assert [f.description for f in result.incidental_findings] == ["Small hepatic cyst"]

    def test_critical_findings_filters_to_critical_only(self) -> None:
        result = self._result()
        assert [f.description for f in result.critical_findings] == ["Large pneumothorax"]

    def test_important_findings_excludes_only_normal(self) -> None:
        result = self._result()
        important = {f.description for f in result.important_findings}
        assert important == {
            "Right lower lobe opacity",
            "Small hepatic cyst",
            "Large pneumothorax",
        }

    def test_is_empty_true_when_every_field_is_vacuous(self) -> None:
        result = self._result(
            examination_summary="",
            findings=(),
            clinical_significance="",
            differential_imaging_considerations=(),
            suggested_follow_up_imaging=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            clinical_reasoning="",
        )
        assert result.is_empty is True

    def test_is_empty_false_when_examination_summary_is_present(self) -> None:
        result = self._result(
            findings=(),
            clinical_significance="",
            differential_imaging_considerations=(),
            suggested_follow_up_imaging=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            clinical_reasoning="",
        )
        assert result.is_empty is False
