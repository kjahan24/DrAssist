"""Tests for `ClinicalRiskAssessmentService`."""

from app.modules.risk_stratification_ai.application.services.clinical_risk_assessment_service import (  # noqa: E501
    ClinicalRiskAssessmentService,
)
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    FakeClinicalRiskPort,
    make_risk_score,
)

_STANDARDIZED_CATEGORIES = frozenset(
    {
        RiskCategory.NEWS2,
        RiskCategory.MEWS,
        RiskCategory.QSOFA,
        RiskCategory.SOFA_SIMPLIFIED,
    }
)


class TestAssessQualitativeRisks:
    def test_returns_empty_tuple_when_port_returns_none(self) -> None:
        service = ClinicalRiskAssessmentService(clinical_risk_port=FakeClinicalRiskPort())
        result = service.assess_qualitative_risks(
            diagnoses=(),
            medical_history=(),
            current_medications=(),
            lab_values=(),
            patient_age=None,
        )
        assert result == ()

    def test_queries_exactly_the_ten_non_standardized_categories(self) -> None:
        port = FakeClinicalRiskPort()
        service = ClinicalRiskAssessmentService(clinical_risk_port=port)

        service.assess_qualitative_risks(
            diagnoses=(),
            medical_history=(),
            current_medications=(),
            lab_values=(),
            patient_age=None,
        )

        assert len(port.calls) == 10
        assert set(port.calls).isdisjoint(_STANDARDIZED_CATEGORIES)

    def test_never_queries_standardized_categories(self) -> None:
        port = FakeClinicalRiskPort()
        service = ClinicalRiskAssessmentService(clinical_risk_port=port)

        service.assess_qualitative_risks(
            diagnoses=(),
            medical_history=(),
            current_medications=(),
            lab_values=(),
            patient_age=None,
        )

        for category in _STANDARDIZED_CATEGORIES:
            assert category not in port.calls

    def test_returns_score_from_port_when_present(self) -> None:
        score = make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=None)
        port = FakeClinicalRiskPort(score=score)
        service = ClinicalRiskAssessmentService(clinical_risk_port=port)

        result = service.assess_qualitative_risks(
            diagnoses=("Sepsis",),
            medical_history=(),
            current_medications=(),
            lab_values=(),
            patient_age=None,
        )

        assert len(result) == 10
        assert all(item is score for item in result)

    def test_passes_through_all_context_arguments(self) -> None:
        received_kwargs: dict[str, object] = {}

        class _RecordingPort(FakeClinicalRiskPort):
            def identify_risk_factors(
                self,
                category: RiskCategory,
                *,
                diagnoses: tuple[str, ...],
                medical_history: tuple[str, ...],
                current_medications: tuple[str, ...],
                lab_values: tuple[object, ...],
                patient_age: int | None,
            ) -> None:
                received_kwargs["diagnoses"] = diagnoses
                received_kwargs["medical_history"] = medical_history
                received_kwargs["current_medications"] = current_medications
                received_kwargs["patient_age"] = patient_age
                return None

        service = ClinicalRiskAssessmentService(clinical_risk_port=_RecordingPort())
        service.assess_qualitative_risks(
            diagnoses=("Sepsis",),
            medical_history=("COPD",),
            current_medications=("Warfarin",),
            lab_values=(),
            patient_age=70,
        )

        assert received_kwargs["diagnoses"] == ("Sepsis",)
        assert received_kwargs["medical_history"] == ("COPD",)
        assert received_kwargs["current_medications"] == ("Warfarin",)
        assert received_kwargs["patient_age"] == 70
