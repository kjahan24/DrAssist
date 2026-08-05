"""Tests for `PatientEducationReportRenderer`."""

import json

from app.modules.patient_education_ai.application.services.patient_education_report_renderer import (  # noqa: E501
    PatientEducationReportRenderer,
)
from app.modules.patient_education_ai.domain.enums import PatientEducationOutputFormat
from tests.unit.modules.patient_education_ai.application.fakes import make_result


class TestSummarize:
    def test_includes_patient_summary(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result(patient_summary="You were seen today for hypertension.")

        summary = renderer.summarize(result)

        assert "You were seen today for hypertension." in summary

    def test_includes_medication_instruction_and_warning_sign_counts(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result(
            medication_instructions=("Take with food.",),
            warning_signs=("Severe headache",),
        )

        summary = renderer.summarize(result)

        assert "1 medication instruction(s)" in summary
        assert "1 warning sign(s)" in summary


class TestRenderJson:
    def test_produces_valid_json(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result()

        payload = json.loads(renderer.render(result, PatientEducationOutputFormat.JSON))

        assert payload["patient_summary"] == result.patient_summary
        assert payload["confidence_score"] == result.confidence_score

    def test_includes_all_list_fields(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result(
            medication_instructions=("Take with food.",),
            home_care_plan=("Rest.",),
            lifestyle_advice=("Limit alcohol.",),
            diet_advice=("Low-sodium.",),
            exercise_advice=("Walk daily.",),
            warning_signs=("Severe headache",),
            emergency_instructions=("Call 911 if chest pain.",),
            follow_up_plan=("See your doctor in 1 week.",),
            patient_checklist=("Fill your prescriptions.",),
        )

        payload = json.loads(renderer.render(result, PatientEducationOutputFormat.JSON))

        assert payload["medication_instructions"] == ["Take with food."]
        assert payload["home_care_plan"] == ["Rest."]
        assert payload["lifestyle_advice"] == ["Limit alcohol."]
        assert payload["diet_advice"] == ["Low-sodium."]
        assert payload["exercise_advice"] == ["Walk daily."]
        assert payload["warning_signs"] == ["Severe headache"]
        assert payload["emergency_instructions"] == ["Call 911 if chest pain."]
        assert payload["follow_up_plan"] == ["See your doctor in 1 week."]
        assert payload["patient_checklist"] == ["Fill your prescriptions."]


class TestRenderMarkdown:
    def test_includes_patient_summary_heading(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result()

        rendered = renderer.render(result, PatientEducationOutputFormat.MARKDOWN)

        assert "## Patient Summary" in rendered

    def test_omits_empty_sections(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result(diagnosis_explanation="", medication_instructions=())

        rendered = renderer.render(result, PatientEducationOutputFormat.MARKDOWN)

        assert "## Diagnosis Explanation" not in rendered
        assert "## Medication Instructions" not in rendered

    def test_includes_populated_sections(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result(
            diagnosis_explanation="Your diagnosis means...",
            medication_instructions=("Take with food.",),
            home_care_plan=("Rest.",),
            lifestyle_advice=("Limit alcohol.",),
            diet_advice=("Low-sodium.",),
            exercise_advice=("Walk daily.",),
            warning_signs=("Severe headache",),
            emergency_instructions=("Call 911.",),
            follow_up_plan=("See your doctor.",),
            patient_checklist=("Fill prescriptions.",),
        )

        rendered = renderer.render(result, PatientEducationOutputFormat.MARKDOWN)

        assert "## Diagnosis Explanation" in rendered
        assert "## Medication Instructions" in rendered
        assert "## Home Care Plan" in rendered
        assert "## Lifestyle Advice" in rendered
        assert "## Diet Advice" in rendered
        assert "## Exercise Advice" in rendered
        assert "## Warning Signs" in rendered
        assert "## Emergency Instructions" in rendered
        assert "## Follow-up Plan" in rendered
        assert "## Patient Checklist" in rendered


class TestRenderText:
    def test_includes_patient_summary_label(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result()

        rendered = renderer.render(result, PatientEducationOutputFormat.TEXT)

        assert "PATIENT SUMMARY:" in rendered

    def test_confidence_not_provided_when_none(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result(confidence_score=None)

        rendered = renderer.render(result, PatientEducationOutputFormat.TEXT)

        assert "Not provided." in rendered

    def test_confidence_formatted_when_present(self) -> None:
        renderer = PatientEducationReportRenderer()
        result = make_result(confidence_score=0.87)

        rendered = renderer.render(result, PatientEducationOutputFormat.TEXT)

        assert "0.87" in rendered
