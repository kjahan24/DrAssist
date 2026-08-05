"""Unit tests for the AI Pathology Interpretation module's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType,
    PathologyFindingCategory,
    PathologyOutputFormat,
    PathologySetting,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    EmptyPathologyReportError,
    InvalidPathologyInterpretationInputError,
    MalformedPathologyReportError,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyFinding,
    PathologyInterpretationInput,
    PathologyInterpretationResult,
)


def _input(**overrides: object) -> PathologyInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "report_text": "Sections show benign glandular tissue with reactive changes noted.",
        "examination_type": PathologyExaminationType.HISTOPATHOLOGY,
        "pathology_setting": PathologySetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return PathologyInterpretationInput(**defaults)  # type: ignore[arg-type]


class TestPathologyInterpretationInput:
    def test_accepts_a_well_formed_input(self) -> None:
        _input()

    def test_raises_when_report_text_is_blank(self) -> None:
        with pytest.raises(EmptyPathologyReportError):
            _input(report_text="   ")

    def test_raises_when_report_text_is_too_short(self) -> None:
        with pytest.raises(MalformedPathologyReportError):
            _input(report_text="short")

    def test_raises_when_report_text_has_no_alphabetic_content(self) -> None:
        with pytest.raises(MalformedPathologyReportError):
            _input(report_text="1234567890!!!!!!")

    def test_accepts_a_report_at_the_minimum_length(self) -> None:
        _input(report_text="No atypia identified in this specimen today.")

    def test_raises_when_language_is_blank(self) -> None:
        with pytest.raises(InvalidPathologyInterpretationInputError):
            _input(language="   ")

    @pytest.mark.parametrize("patient_age", [-1, 151])
    def test_raises_when_patient_age_is_out_of_range(self, patient_age: int) -> None:
        with pytest.raises(InvalidPathologyInterpretationInputError):
            _input(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 150, 42])
    def test_accepts_boundary_patient_ages(self, patient_age: int) -> None:
        _input(patient_age=patient_age)

    def test_accepts_a_missing_patient_age(self) -> None:
        _input(patient_age=None)

    def test_carries_through_examination_type(self) -> None:
        input_dto = _input(examination_type=PathologyExaminationType.FNAC)
        assert input_dto.examination_type is PathologyExaminationType.FNAC

    def test_accepts_laboratory_radiology_and_medical_reasoning_context_as_plain_text(
        self,
    ) -> None:
        input_dto = _input(
            laboratory_interpretation="CA-125 elevated.",
            radiology_interpretation="Adnexal mass noted on ultrasound.",
            medical_reasoning_context="High pretest probability of ovarian malignancy.",
        )
        assert input_dto.laboratory_interpretation == "CA-125 elevated."
        assert input_dto.radiology_interpretation == "Adnexal mass noted on ultrasound."
        assert input_dto.medical_reasoning_context == (
            "High pretest probability of ovarian malignancy."
        )


class TestPathologyFinding:
    def test_carries_its_fields(self) -> None:
        finding = PathologyFinding(
            description="Invasive carcinoma",
            category=PathologyFindingCategory.MALIGNANT,
            anatomical_site="Left breast, upper outer quadrant",
        )
        assert finding.category is PathologyFindingCategory.MALIGNANT
        assert finding.anatomical_site == "Left breast, upper outer quadrant"

    def test_anatomical_site_defaults_to_none(self) -> None:
        finding = PathologyFinding(description="x", category=PathologyFindingCategory.BENIGN)
        assert finding.anatomical_site is None


class TestPathologyInterpretationResult:
    def _result(self, **overrides: object) -> PathologyInterpretationResult:
        defaults: dict[str, object] = {
            "pathology_summary": "Findings reviewed.",
            "key_findings": ("Invasive carcinoma identified",),
            "microscopic_findings": (
                PathologyFinding(
                    description="Benign glandular tissue",
                    category=PathologyFindingCategory.BENIGN,
                ),
                PathologyFinding(
                    description="Invasive ductal carcinoma",
                    category=PathologyFindingCategory.MALIGNANT,
                ),
                PathologyFinding(
                    description="Atypical ductal hyperplasia",
                    category=PathologyFindingCategory.ATYPICAL,
                ),
            ),
            "final_impression": "Invasive ductal carcinoma.",
            "clinical_significance": "Requires oncologic correlation.",
            "correlation_recommendations": (),
            "suggested_follow_up": (),
            "suggested_specialist_referral": (),
            "red_flag_warnings": (),
            "confidence_score": 0.7,
            "clinical_reasoning": "Grounded in the described architecture.",
            "raw_text": "{}",
            "output_format": PathologyOutputFormat.JSON,
        }
        defaults.update(overrides)
        return PathologyInterpretationResult(**defaults)  # type: ignore[arg-type]

    def test_benign_features_filters_to_benign_only(self) -> None:
        result = self._result()
        assert [f.description for f in result.benign_features] == ["Benign glandular tissue"]

    def test_malignant_features_filters_to_malignant_only(self) -> None:
        result = self._result()
        assert [f.description for f in result.malignant_features] == ["Invasive ductal carcinoma"]

    def test_atypical_findings_filters_to_atypical_only(self) -> None:
        result = self._result()
        assert [f.description for f in result.atypical_findings] == ["Atypical ductal hyperplasia"]

    def test_is_empty_true_when_every_field_is_vacuous(self) -> None:
        result = self._result(
            pathology_summary="",
            key_findings=(),
            microscopic_findings=(),
            final_impression="",
            clinical_significance="",
            correlation_recommendations=(),
            suggested_follow_up=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            clinical_reasoning="",
        )
        assert result.is_empty is True

    def test_is_empty_false_when_pathology_summary_is_present(self) -> None:
        result = self._result(
            key_findings=(),
            microscopic_findings=(),
            final_impression="",
            clinical_significance="",
            correlation_recommendations=(),
            suggested_follow_up=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            clinical_reasoning="",
        )
        assert result.is_empty is False
