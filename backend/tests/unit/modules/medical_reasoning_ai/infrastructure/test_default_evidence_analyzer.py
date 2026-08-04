"""Unit tests for `DefaultEvidenceAnalyzer`."""

from uuid import uuid4

import pytest

from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    ReasoningSetting,
    RedFlagPriority,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    MedicalReasoningInput,
    RedFlag,
)
from app.modules.medical_reasoning_ai.infrastructure.reasoning.default_evidence_analyzer import (
    DefaultEvidenceAnalyzer,
)


def _evidence(**overrides: object) -> MedicalReasoningInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "reasoning_setting": ReasoningSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return MedicalReasoningInput(**defaults)  # type: ignore[arg-type]


class TestWeightEvidenceItem:
    def test_boosts_weight_for_objective_language(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()
        item = EvidenceItem(
            description="Troponin elevated at 0.5 mg/dL",
            weight=0.5,
            polarity=EvidencePolarity.SUPPORTING,
        )

        weighted = analyzer.weight_evidence_item(item)

        assert weighted.weight > 0.5

    def test_does_not_boost_purely_subjective_language(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()
        item = EvidenceItem(
            description="Patient reports feeling unwell",
            weight=0.5,
            polarity=EvidencePolarity.SUPPORTING,
        )

        weighted = analyzer.weight_evidence_item(item)

        assert weighted.weight == 0.5

    def test_caps_weight_at_one(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()
        item = EvidenceItem(
            description="HR: 110 bpm", weight=0.95, polarity=EvidencePolarity.SUPPORTING
        )

        weighted = analyzer.weight_evidence_item(item)

        assert weighted.weight <= 1.0

    def test_preserves_description_and_polarity(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()
        item = EvidenceItem(
            description="HR: 110 bpm", weight=0.5, polarity=EvidencePolarity.CONTRADICTING
        )

        weighted = analyzer.weight_evidence_item(item)

        assert weighted.description == "HR: 110 bpm"
        assert weighted.polarity is EvidencePolarity.CONTRADICTING


class TestIdentifyMissingInformation:
    def test_flags_missing_narrative_content(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(_evidence())

        assert any("hpi" in item.lower() for item in missing)

    def test_no_narrative_flag_when_symptoms_given(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(_evidence(symptoms=("chest pain",)))

        assert not any("hpi" in item.lower() for item in missing)

    def test_flags_missing_objective_content(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(_evidence())

        assert any("physical examination" in item.lower() for item in missing)

    def test_no_objective_flag_when_vitals_given(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(_evidence(vitals={"HR": "80"}))

        assert not any("physical examination" in item.lower() for item in missing)

    def test_flags_missing_labs_and_imaging(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(_evidence())

        assert any("laboratory" in item.lower() for item in missing)

    def test_no_labs_flag_when_laboratory_results_given(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(
            _evidence(laboratory_results=("WBC: 11.2",))
        )

        assert not any("laboratory" in item.lower() for item in missing)

    def test_flags_missing_allergy_and_medication_information(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(_evidence())

        assert any("allergy or medication" in item.lower() for item in missing)

    def test_no_allergy_flag_when_allergies_given(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(_evidence(allergies=("penicillin",)))

        assert not any("allergy or medication" in item.lower() for item in missing)

    def test_no_missing_information_when_fully_populated(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        missing = analyzer.identify_missing_information(
            _evidence(
                history_of_present_illness="Gradual onset",
                physical_examination="Unremarkable",
                laboratory_results=("WBC: 11.2",),
                allergies=("none known",),
            )
        )

        assert missing == ()


class TestComputeRiskScore:
    def test_zero_risk_factors_and_flags_is_zero_score(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        score = analyzer.compute_risk_score(risk_factors=(), red_flags=())

        assert score == 0.0

    def test_higher_priority_flags_contribute_more(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        low_score = analyzer.compute_risk_score(
            risk_factors=(), red_flags=(RedFlag(description="x", priority=RedFlagPriority.LOW),)
        )
        critical_score = analyzer.compute_risk_score(
            risk_factors=(),
            red_flags=(RedFlag(description="x", priority=RedFlagPriority.CRITICAL),),
        )

        assert critical_score > low_score

    def test_risk_factors_contribute_to_the_score(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()

        score = analyzer.compute_risk_score(risk_factors=("diabetes", "smoking"), red_flags=())

        assert score > 0.0

    def test_score_is_capped_at_one(self) -> None:
        analyzer = DefaultEvidenceAnalyzer()
        many_flags = tuple(
            RedFlag(description=f"flag-{i}", priority=RedFlagPriority.CRITICAL) for i in range(10)
        )

        score = analyzer.compute_risk_score(risk_factors=(), red_flags=many_flags)

        assert score == pytest.approx(1.0)
