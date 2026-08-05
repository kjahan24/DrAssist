"""Unit tests for `StaticPatientEducationKnowledgeBase`."""

import pytest

from app.modules.patient_education_ai.infrastructure.patient_education.static_patient_education_knowledge_base import (  # noqa: E501
    StaticPatientEducationKnowledgeBase,
)

_KB = StaticPatientEducationKnowledgeBase()

_RECOGNIZED_DIAGNOSES = (
    "hypertension",
    "diabetes",
    "asthma",
    "copd",
    "heart failure",
    "pneumonia",
    "urinary tract infection",
    "coronary artery disease",
    "chronic kidney disease",
    "stroke",
)


class TestExplainDiagnosis:
    @pytest.mark.parametrize("diagnosis", _RECOGNIZED_DIAGNOSES)
    def test_returns_an_explanation_for_every_recognized_diagnosis(self, diagnosis: str) -> None:
        explanation = _KB.explain_diagnosis(diagnosis)
        assert explanation is not None
        assert explanation.strip()

    def test_returns_none_for_an_unrecognized_diagnosis(self) -> None:
        assert _KB.explain_diagnosis("Some Unrecognized Condition") is None

    def test_matches_case_insensitively(self) -> None:
        assert _KB.explain_diagnosis("HYPERTENSION") is not None

    def test_matches_by_substring(self) -> None:
        assert _KB.explain_diagnosis("Essential Hypertension, stage 2") is not None


class TestIdentifyWarningSigns:
    @pytest.mark.parametrize("diagnosis", _RECOGNIZED_DIAGNOSES)
    def test_returns_warning_signs_for_every_recognized_diagnosis(self, diagnosis: str) -> None:
        assert len(_KB.identify_warning_signs(diagnosis)) > 0

    def test_returns_empty_tuple_for_an_unrecognized_diagnosis(self) -> None:
        assert _KB.identify_warning_signs("Some Unrecognized Condition") == ()


class TestIdentifyEmergencySymptoms:
    @pytest.mark.parametrize("diagnosis", _RECOGNIZED_DIAGNOSES)
    def test_returns_emergency_symptoms_for_every_recognized_diagnosis(
        self, diagnosis: str
    ) -> None:
        assert len(_KB.identify_emergency_symptoms(diagnosis)) > 0

    def test_returns_empty_tuple_for_an_unrecognized_diagnosis(self) -> None:
        assert _KB.identify_emergency_symptoms("Some Unrecognized Condition") == ()
