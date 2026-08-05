"""Tests for `PatientEducationService`."""

from app.modules.patient_education_ai.application.services.patient_education_service import (
    PatientEducationService,
)
from tests.unit.modules.patient_education_ai.application.fakes import FakePatientEducationPort


class TestBuildDiagnosisExplanation:
    def test_returns_empty_string_when_no_diagnosis_recognized(self) -> None:
        service = PatientEducationService(education_port=FakePatientEducationPort())
        assert service.build_diagnosis_explanation(("Unknown Diagnosis",)) == ""

    def test_returns_curated_explanation_for_a_single_diagnosis(self) -> None:
        port = FakePatientEducationPort(explanation="Plain-language explanation.")
        service = PatientEducationService(education_port=port)

        result = service.build_diagnosis_explanation(("Hypertension",))

        assert result == "Plain-language explanation."

    def test_combines_explanations_for_multiple_diagnoses(self) -> None:
        port = FakePatientEducationPort(explanation="Explanation.")
        service = PatientEducationService(education_port=port)

        result = service.build_diagnosis_explanation(("Hypertension", "Diabetes"))

        assert result == "Explanation. Explanation."

    def test_queries_port_once_per_diagnosis(self) -> None:
        port = FakePatientEducationPort(explanation="Explanation.")
        service = PatientEducationService(education_port=port)

        service.build_diagnosis_explanation(("Hypertension", "Diabetes"))

        assert port.explain_calls == ["Hypertension", "Diabetes"]


class TestCollectWarningSigns:
    def test_returns_empty_tuple_when_none_recognized(self) -> None:
        service = PatientEducationService(education_port=FakePatientEducationPort())
        assert service.collect_warning_signs(("Unknown",)) == ()

    def test_returns_curated_warning_signs(self) -> None:
        port = FakePatientEducationPort(warning_signs=("Severe headache",))
        service = PatientEducationService(education_port=port)

        assert service.collect_warning_signs(("Hypertension",)) == ("Severe headache",)

    def test_deduplicates_across_diagnoses(self) -> None:
        port = FakePatientEducationPort(warning_signs=("Severe headache",))
        service = PatientEducationService(education_port=port)

        result = service.collect_warning_signs(("Hypertension", "Stroke"))

        assert result == ("Severe headache",)


class TestCollectEmergencySymptoms:
    def test_returns_empty_tuple_when_none_recognized(self) -> None:
        service = PatientEducationService(education_port=FakePatientEducationPort())
        assert service.collect_emergency_symptoms(("Unknown",)) == ()

    def test_returns_curated_emergency_symptoms(self) -> None:
        port = FakePatientEducationPort(emergency_symptoms=("Chest pain at rest",))
        service = PatientEducationService(education_port=port)

        assert service.collect_emergency_symptoms(("Hypertension",)) == ("Chest pain at rest",)
