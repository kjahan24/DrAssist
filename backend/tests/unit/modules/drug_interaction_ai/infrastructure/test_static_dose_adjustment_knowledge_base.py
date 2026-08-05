"""Unit tests for `StaticDoseAdjustmentKnowledgeBase`."""

from app.modules.drug_interaction_ai.domain.value_objects import MedicationEntry
from app.modules.drug_interaction_ai.infrastructure.dose_adjustment.static_dose_adjustment_knowledge_base import (  # noqa: E501
    StaticDoseAdjustmentKnowledgeBase,
)


def _medication(**overrides: object) -> MedicationEntry:
    defaults: dict[str, object] = {"drug_name": "Metformin"}
    defaults.update(overrides)
    return MedicationEntry(**defaults)  # type: ignore[arg-type]


class TestSuggestDoseAdjustmentRenal:
    def test_suggests_adjustment_for_a_renally_cleared_drug_with_impaired_function(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Metformin"),
            renal_function="Renal failure",
            hepatic_function=None,
        )

        assert result is not None
        assert "renal" in result.lower()

    def test_suggests_adjustment_for_a_low_egfr_value(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Digoxin"),
            renal_function="eGFR: 25 mL/min/1.73m2",
            hepatic_function=None,
        )

        assert result is not None

    def test_no_suggestion_for_a_normal_egfr_value(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Digoxin"),
            renal_function="eGFR: 90 mL/min/1.73m2",
            hepatic_function=None,
        )

        assert result is None

    def test_no_suggestion_when_renal_function_is_not_given(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Metformin"), renal_function=None, hepatic_function=None
        )

        assert result is None

    def test_no_suggestion_for_a_non_renally_cleared_drug(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Warfarin"),
            renal_function="Severe renal failure",
            hepatic_function=None,
        )

        assert result is None


class TestSuggestDoseAdjustmentHepatic:
    def test_suggests_adjustment_for_a_hepatically_cleared_drug_with_impaired_function(
        self,
    ) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Acetaminophen"),
            renal_function=None,
            hepatic_function="Hepatic impairment",
        )

        assert result is not None
        assert "hepatic" in result.lower()

    def test_no_suggestion_for_normal_liver_function(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Acetaminophen"),
            renal_function=None,
            hepatic_function="Normal liver function",
        )

        assert result is None

    def test_no_suggestion_when_hepatic_function_is_not_given(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()

        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Acetaminophen"), renal_function=None, hepatic_function=None
        )

        assert result is None


class TestSuggestDoseAdjustmentKeywords:
    def test_recognizes_ckd_keyword(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()
        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Gabapentin"), renal_function="CKD stage 4", hepatic_function=None
        )
        assert result is not None

    def test_recognizes_insufficiency_keyword(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()
        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Gabapentin"),
            renal_function="Renal insufficiency noted",
            hepatic_function=None,
        )
        assert result is not None

    def test_blank_string_is_treated_as_not_provided(self) -> None:
        kb = StaticDoseAdjustmentKnowledgeBase()
        result = kb.suggest_dose_adjustment(
            _medication(drug_name="Metformin"), renal_function="   ", hepatic_function=None
        )
        assert result is None
