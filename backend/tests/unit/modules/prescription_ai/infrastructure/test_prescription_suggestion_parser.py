"""Unit tests for `DefaultPrescriptionSuggestionParser`."""

import json

import pytest

from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.exceptions import InvalidPrescriptionResponseFormatError
from app.modules.prescription_ai.infrastructure.parsing.prescription_suggestion_parser import (
    DefaultPrescriptionSuggestionParser,
)

_VALID_PAYLOAD = {
    "medications": [
        {
            "generic_name": "amoxicillin",
            "brand_name": "Amoxil",
            "strength": "500mg",
            "dosage": "1 capsule",
            "route": "oral",
            "frequency": "three times daily",
            "duration": "7 days",
            "quantity": "21 capsules",
            "is_prn": False,
            "clinical_indication": "Acute pharyngitis",
            "monitoring_advice": "Watch for rash",
            "patient_instructions": "Take with food",
            "confidence_score": 0.9,
            "clinical_reasoning": "First-line for bacterial pharyngitis",
        }
    ],
    "safety_findings": [
        {
            "category": "allergy_conflict",
            "severity": "high",
            "description": "Cross-reactive with penicillin allergy",
            "affected_medications": ["amoxicillin"],
        }
    ],
    "monitoring_recommendations": ["Recheck symptoms in 48 hours"],
    "follow_up_recommendations": ["Return if no improvement"],
}


class TestParsePlainJSON:
    def test_parses_all_medication_fields(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()

        suggestion_set = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=PrescriptionOutputFormat.JSON
        )

        medication = suggestion_set.medications[0]
        assert medication.generic_name == "amoxicillin"
        assert medication.brand_name == "Amoxil"
        assert medication.route is AdministrationRoute.ORAL
        assert medication.is_prn is False
        assert medication.confidence_score == 0.9

    def test_parses_safety_findings(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()

        suggestion_set = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=PrescriptionOutputFormat.JSON
        )

        finding = suggestion_set.safety_findings[0]
        assert finding.category is SafetyFindingCategory.ALLERGY_CONFLICT
        assert finding.severity is SafetySeverity.HIGH
        assert finding.affected_medications == ("amoxicillin",)

    def test_parses_monitoring_and_follow_up_recommendations(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()

        suggestion_set = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.monitoring_recommendations == ("Recheck symptoms in 48 hours",)
        assert suggestion_set.follow_up_recommendations == ("Return if no improvement",)

    def test_carries_through_the_requested_output_format(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()

        suggestion_set = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=PrescriptionOutputFormat.MARKDOWN
        )

        assert suggestion_set.output_format is PrescriptionOutputFormat.MARKDOWN

    def test_preserves_the_original_raw_text(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        raw_text = json.dumps(_VALID_PAYLOAD)

        suggestion_set = parser.parse(raw_text, output_format=PrescriptionOutputFormat.JSON)

        assert suggestion_set.raw_text == raw_text

    def test_empty_medications_array_parses_to_an_empty_set(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()

        suggestion_set = parser.parse(
            json.dumps({"medications": []}), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.medications == ()

    def test_missing_optional_top_level_keys_default_to_empty(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()

        suggestion_set = parser.parse(
            json.dumps({"medications": []}), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.safety_findings == ()
        assert suggestion_set.monitoring_recommendations == ()
        assert suggestion_set.follow_up_recommendations == ()


class TestParseFencedJSON:
    def test_parses_json_wrapped_in_a_labeled_fence(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        raw = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"

        suggestion_set = parser.parse(raw, output_format=PrescriptionOutputFormat.JSON)

        assert suggestion_set.medications[0].generic_name == "amoxicillin"

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        raw = f"```\n{json.dumps(_VALID_PAYLOAD)}\n```"

        suggestion_set = parser.parse(raw, output_format=PrescriptionOutputFormat.JSON)

        assert suggestion_set.medications[0].generic_name == "amoxicillin"


class TestParseMissingOrMalformedFields:
    def test_missing_fields_in_a_medication_become_empty_or_none(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        payload = {"medications": [{"generic_name": "amoxicillin"}]}

        suggestion_set = parser.parse(
            json.dumps(payload), output_format=PrescriptionOutputFormat.JSON
        )

        medication = suggestion_set.medications[0]
        assert medication.generic_name == "amoxicillin"
        assert medication.brand_name is None
        assert medication.dosage == ""
        assert medication.route is AdministrationRoute.OTHER
        assert medication.is_prn is False
        assert medication.confidence_score is None

    def test_a_boolean_confidence_score_is_not_treated_as_a_number(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        payload = {"medications": [{"generic_name": "amoxicillin", "confidence_score": True}]}

        suggestion_set = parser.parse(
            json.dumps(payload), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.medications[0].confidence_score is None

    def test_an_unrecognized_route_defaults_to_other(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        payload = {"medications": [{"generic_name": "amoxicillin", "route": "not-a-route"}]}

        suggestion_set = parser.parse(
            json.dumps(payload), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.medications[0].route is AdministrationRoute.OTHER

    def test_non_dict_items_in_the_medications_array_are_skipped(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        payload = {"medications": ["not-an-object", {"generic_name": "amoxicillin"}]}

        suggestion_set = parser.parse(
            json.dumps(payload), output_format=PrescriptionOutputFormat.JSON
        )

        assert len(suggestion_set.medications) == 1

    def test_a_safety_finding_with_an_unrecognized_category_is_skipped(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        payload = {
            "medications": [],
            "safety_findings": [{"category": "not-a-category", "description": "x"}],
        }

        suggestion_set = parser.parse(
            json.dumps(payload), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.safety_findings == ()

    def test_a_safety_finding_with_an_unrecognized_severity_defaults_to_moderate(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        payload = {
            "medications": [],
            "safety_findings": [
                {
                    "category": "drug_interaction",
                    "severity": "not-a-severity",
                    "description": "x",
                }
            ],
        }

        suggestion_set = parser.parse(
            json.dumps(payload), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.safety_findings[0].severity is SafetySeverity.MODERATE

    def test_non_string_entries_in_recommendation_lists_are_dropped(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        payload = {
            "medications": [],
            "monitoring_recommendations": ["valid", 42, None, "  "],
        }

        suggestion_set = parser.parse(
            json.dumps(payload), output_format=PrescriptionOutputFormat.JSON
        )

        assert suggestion_set.monitoring_recommendations == ("valid",)


class TestParseFailures:
    def test_raises_on_malformed_json(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        with pytest.raises(InvalidPrescriptionResponseFormatError):
            parser.parse("not json at all", output_format=PrescriptionOutputFormat.JSON)

    def test_raises_on_empty_response(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        with pytest.raises(InvalidPrescriptionResponseFormatError):
            parser.parse("   ", output_format=PrescriptionOutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_list_not_an_object(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        with pytest.raises(InvalidPrescriptionResponseFormatError):
            parser.parse("[1, 2, 3]", output_format=PrescriptionOutputFormat.JSON)

    def test_raises_when_medications_key_is_missing(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        with pytest.raises(InvalidPrescriptionResponseFormatError):
            parser.parse(
                json.dumps({"not_medications": []}), output_format=PrescriptionOutputFormat.JSON
            )

    def test_raises_when_medications_is_not_a_list(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        with pytest.raises(InvalidPrescriptionResponseFormatError):
            parser.parse(
                json.dumps({"medications": "not-a-list"}),
                output_format=PrescriptionOutputFormat.JSON,
            )

    def test_raises_on_truncated_json(self) -> None:
        parser = DefaultPrescriptionSuggestionParser()
        truncated = json.dumps(_VALID_PAYLOAD)[:-5]
        with pytest.raises(InvalidPrescriptionResponseFormatError):
            parser.parse(truncated, output_format=PrescriptionOutputFormat.JSON)
