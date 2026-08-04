"""Unit tests for `DefaultClinicalReasoningAdvisor`."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis_ai.domain.enums import ClinicalSetting, UrgencyLevel
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput
from app.modules.differential_diagnosis_ai.infrastructure.reasoning.clinical_reasoning_advisor import (  # noqa: E501
    DefaultClinicalReasoningAdvisor,
)


def _evidence(**overrides: object) -> DifferentialDiagnosisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "clinical_setting": ClinicalSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


class TestClassifyMinimumUrgency:
    def test_no_red_flags_is_always_routine(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        result = advisor.classify_minimum_urgency(red_flag_indicators=(), confidence_score=0.99)

        assert result is UrgencyLevel.ROUTINE

    def test_red_flags_with_low_confidence_is_urgent(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        result = advisor.classify_minimum_urgency(
            red_flag_indicators=("hypotension",), confidence_score=0.3
        )

        assert result is UrgencyLevel.URGENT

    def test_red_flags_with_high_confidence_is_emergent(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        result = advisor.classify_minimum_urgency(
            red_flag_indicators=("hypotension",), confidence_score=0.9
        )

        assert result is UrgencyLevel.EMERGENT

    def test_red_flags_with_none_confidence_is_urgent(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        result = advisor.classify_minimum_urgency(
            red_flag_indicators=("hypotension",), confidence_score=None
        )

        assert result is UrgencyLevel.URGENT

    @pytest.mark.parametrize("confidence_score", [0.7, 0.8, 1.0])
    def test_boundary_high_confidence_values_are_emergent(self, confidence_score: float) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        result = advisor.classify_minimum_urgency(
            red_flag_indicators=("chest pain radiating to jaw",),
            confidence_score=confidence_score,
        )

        assert result is UrgencyLevel.EMERGENT


class TestIdentifyMissingInformation:
    def test_flags_missing_narrative_content(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(_evidence())

        assert any("hpi" in item.lower() for item in missing)

    def test_no_narrative_flag_when_symptoms_given(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(_evidence(symptoms=("chest pain",)))

        assert not any("hpi" in item.lower() for item in missing)

    def test_flags_missing_objective_content(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(_evidence())

        assert any("physical examination" in item.lower() for item in missing)

    def test_no_objective_flag_when_vitals_given(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(_evidence(vitals={"HR": "80"}))

        assert not any("physical examination" in item.lower() for item in missing)

    def test_flags_missing_labs_and_imaging(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(_evidence())

        assert any("laboratory" in item.lower() for item in missing)

    def test_no_labs_flag_when_laboratory_results_given(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(_evidence(laboratory_results=("WBC: 11.2",)))

        assert not any("laboratory" in item.lower() for item in missing)

    def test_no_labs_flag_when_imaging_summary_given(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(
            _evidence(imaging_summary="CXR unremarkable")
        )

        assert not any("laboratory" in item.lower() for item in missing)

    def test_no_missing_information_when_fully_populated(self) -> None:
        advisor = DefaultClinicalReasoningAdvisor()

        missing = advisor.identify_missing_information(
            _evidence(
                history_of_present_illness="Gradual onset",
                physical_examination="Unremarkable",
                laboratory_results=("WBC: 11.2",),
            )
        )

        assert missing == ()
