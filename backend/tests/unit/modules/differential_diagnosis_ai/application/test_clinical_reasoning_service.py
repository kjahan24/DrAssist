"""Unit tests for `ClinicalReasoningService` — the deterministic half of
this task's own "CLINICAL REASONING" requirement."""

from app.modules.differential_diagnosis_ai.application.services.clinical_reasoning_service import (
    ClinicalReasoningService,
)
from app.modules.differential_diagnosis_ai.domain.enums import ClinicalSetting, UrgencyLevel
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    FakeClinicalReasoningPort,
    make_candidate,
)


def _evidence(**overrides: object) -> DifferentialDiagnosisInput:
    from uuid import uuid4

    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "clinical_setting": ClinicalSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


class TestUpgradeUrgencyLevels:
    def test_upgrades_a_candidate_below_the_deterministic_minimum(self) -> None:
        port = FakeClinicalReasoningPort(minimum_urgency=UrgencyLevel.EMERGENT)
        service = ClinicalReasoningService(reasoning=port)
        candidate = make_candidate(urgency_level=UrgencyLevel.ROUTINE)

        upgraded = service.upgrade_urgency_levels((candidate,))

        assert upgraded[0].urgency_level is UrgencyLevel.EMERGENT

    def test_does_not_downgrade_a_candidate_above_the_deterministic_minimum(self) -> None:
        port = FakeClinicalReasoningPort(minimum_urgency=UrgencyLevel.ROUTINE)
        service = ClinicalReasoningService(reasoning=port)
        candidate = make_candidate(urgency_level=UrgencyLevel.EMERGENT)

        upgraded = service.upgrade_urgency_levels((candidate,))

        assert upgraded[0].urgency_level is UrgencyLevel.EMERGENT

    def test_leaves_a_candidate_already_at_the_minimum_unchanged(self) -> None:
        port = FakeClinicalReasoningPort(minimum_urgency=UrgencyLevel.URGENT)
        service = ClinicalReasoningService(reasoning=port)
        candidate = make_candidate(urgency_level=UrgencyLevel.URGENT)

        upgraded = service.upgrade_urgency_levels((candidate,))

        assert upgraded[0].urgency_level is UrgencyLevel.URGENT

    def test_passes_red_flags_and_confidence_to_the_port(self) -> None:
        port = FakeClinicalReasoningPort()
        service = ClinicalReasoningService(reasoning=port)
        candidate = make_candidate(red_flag_indicators=("hypotension",), confidence_score=0.8)

        service.upgrade_urgency_levels((candidate,))

        assert port.urgency_calls[0]["red_flag_indicators"] == ("hypotension",)
        assert port.urgency_calls[0]["confidence_score"] == 0.8

    def test_preserves_candidate_order(self) -> None:
        port = FakeClinicalReasoningPort()
        service = ClinicalReasoningService(reasoning=port)
        first = make_candidate(disease_name="A")
        second = make_candidate(disease_name="B")

        upgraded = service.upgrade_urgency_levels((first, second))

        assert [c.disease_name for c in upgraded] == ["A", "B"]


class TestAssessMissingInformation:
    def test_delegates_to_the_port(self) -> None:
        port = FakeClinicalReasoningPort(missing_information=("no labs provided",))
        service = ClinicalReasoningService(reasoning=port)

        missing = service.assess_missing_information(_evidence())

        assert missing == ("no labs provided",)
