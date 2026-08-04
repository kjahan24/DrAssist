"""Unit tests for `PrescriptionSuggestionRenderer`."""

import json

from app.modules.prescription_ai.application.services.prescription_suggestion_renderer import (
    PrescriptionSuggestionRenderer,
)
from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSafetyFinding,
    MedicationSuggestion,
    PrescriptionSuggestionSet,
)


def _suggestion_set(**overrides: object) -> PrescriptionSuggestionSet:
    defaults: dict[str, object] = {
        "medications": (
            MedicationSuggestion(
                generic_name="amoxicillin",
                brand_name="Amoxil",
                strength="500mg",
                dosage="1 capsule",
                route=AdministrationRoute.ORAL,
                frequency="three times daily",
                duration="7 days",
                quantity="21 capsules",
                is_prn=False,
                clinical_indication="Acute pharyngitis",
                monitoring_advice="Watch for rash",
                patient_instructions="Take with food",
                confidence_score=0.9,
                clinical_reasoning="First-line for bacterial pharyngitis",
            ),
        ),
        "safety_findings": (
            MedicationSafetyFinding(
                category=SafetyFindingCategory.ALLERGY_CONFLICT,
                severity=SafetySeverity.HIGH,
                description="Cross-reactive with penicillin allergy",
                affected_medications=("amoxicillin",),
            ),
        ),
        "monitoring_recommendations": ("Recheck symptoms in 48 hours",),
        "follow_up_recommendations": ("Return if no improvement in 3 days",),
        "raw_text": "{}",
        "output_format": PrescriptionOutputFormat.JSON,
    }
    defaults.update(overrides)
    return PrescriptionSuggestionSet(**defaults)  # type: ignore[arg-type]


class TestPrescriptionSuggestionRendererJSON:
    def test_renders_valid_json_with_medications_and_findings(self) -> None:
        result = PrescriptionSuggestionRenderer().render(
            _suggestion_set(), PrescriptionOutputFormat.JSON
        )

        payload = json.loads(result)
        assert payload["medications"][0]["generic_name"] == "amoxicillin"
        assert payload["medications"][0]["route"] == "oral"
        assert payload["safety_findings"][0]["category"] == "allergy_conflict"
        assert payload["monitoring_recommendations"] == ["Recheck symptoms in 48 hours"]
        assert payload["follow_up_recommendations"] == ["Return if no improvement in 3 days"]

    def test_null_confidence_score_round_trips_as_json_null(self) -> None:
        suggestion_set = _suggestion_set(
            medications=(
                MedicationSuggestion(
                    generic_name="amoxicillin",
                    brand_name=None,
                    strength="500mg",
                    dosage="1 capsule",
                    route=AdministrationRoute.ORAL,
                    frequency="three times daily",
                    duration="7 days",
                    quantity="21 capsules",
                    is_prn=False,
                    clinical_indication="Acute pharyngitis",
                    monitoring_advice="Watch for rash",
                    patient_instructions="Take with food",
                    confidence_score=None,
                    clinical_reasoning="First-line for bacterial pharyngitis",
                ),
            )
        )

        result = PrescriptionSuggestionRenderer().render(
            suggestion_set, PrescriptionOutputFormat.JSON
        )

        assert json.loads(result)["medications"][0]["confidence_score"] is None


class TestPrescriptionSuggestionRendererMarkdown:
    def test_renders_a_heading_per_medication(self) -> None:
        result = PrescriptionSuggestionRenderer().render(
            _suggestion_set(), PrescriptionOutputFormat.MARKDOWN
        )

        assert "## amoxicillin (Amoxil)" in result
        assert "**Dosage:** 1 capsule" in result

    def test_includes_safety_findings_section(self) -> None:
        result = PrescriptionSuggestionRenderer().render(
            _suggestion_set(), PrescriptionOutputFormat.MARKDOWN
        )

        assert "## Safety Findings" in result
        assert "allergy_conflict" in result

    def test_includes_monitoring_and_follow_up_sections(self) -> None:
        result = PrescriptionSuggestionRenderer().render(
            _suggestion_set(), PrescriptionOutputFormat.MARKDOWN
        )

        assert "## Monitoring Recommendations" in result
        assert "## Follow-up Recommendations" in result

    def test_omits_optional_sections_when_empty(self) -> None:
        suggestion_set = _suggestion_set(
            safety_findings=(), monitoring_recommendations=(), follow_up_recommendations=()
        )

        result = PrescriptionSuggestionRenderer().render(
            suggestion_set, PrescriptionOutputFormat.MARKDOWN
        )

        assert "Safety Findings" not in result
        assert "Monitoring Recommendations" not in result


class TestPrescriptionSuggestionRendererText:
    def test_renders_uppercased_generic_name_and_labels(self) -> None:
        result = PrescriptionSuggestionRenderer().render(
            _suggestion_set(), PrescriptionOutputFormat.TEXT
        )

        assert "AMOXICILLIN" in result
        assert "DOSAGE: 1 capsule" in result
        assert "SAFETY FINDINGS:" in result

    def test_marks_prn_medications(self) -> None:
        suggestion_set = _suggestion_set(
            medications=(
                MedicationSuggestion(
                    generic_name="ibuprofen",
                    brand_name=None,
                    strength="200mg",
                    dosage="1 tablet",
                    route=AdministrationRoute.ORAL,
                    frequency="every 6 hours as needed",
                    duration="5 days",
                    quantity="20 tablets",
                    is_prn=True,
                    clinical_indication="Pain",
                    monitoring_advice="Take with food",
                    patient_instructions="Do not exceed 4 doses per day",
                    confidence_score=0.7,
                    clinical_reasoning="Symptomatic relief",
                ),
            )
        )

        result = PrescriptionSuggestionRenderer().render(
            suggestion_set, PrescriptionOutputFormat.TEXT
        )

        assert "[PRN]" in result
