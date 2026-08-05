"""Unit tests for `ContraindicationService`."""

from app.modules.drug_interaction_ai.application.services.contraindication_service import (
    ContraindicationService,
)
from app.modules.drug_interaction_ai.domain.enums import SafetyIssueCategory
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    FakeMedicationSafetyPort,
    make_medication,
)


class TestDetectDuplicateTherapy:
    def test_no_issue_for_a_single_medication(self) -> None:
        service = ContraindicationService(port=FakeMedicationSafetyPort())
        assert service.detect_duplicate_therapy((make_medication(),)) == ()

    def test_flags_the_same_drug_name_reported_twice(self) -> None:
        service = ContraindicationService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin"),
            make_medication(drug_name="Warfarin", dose="10mg"),
        )

        issues = service.detect_duplicate_therapy(medications)

        assert len(issues) == 1
        assert issues[0].category is SafetyIssueCategory.DUPLICATE_THERAPY

    def test_is_case_insensitive(self) -> None:
        service = ContraindicationService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin"),
            make_medication(drug_name="WARFARIN"),
        )
        assert len(service.detect_duplicate_therapy(medications)) == 1

    def test_no_issue_for_two_different_drugs(self) -> None:
        service = ContraindicationService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin"),
            make_medication(drug_name="Aspirin"),
        )
        assert service.detect_duplicate_therapy(medications) == ()

    def test_flags_new_prescription_duplicating_current_medications(self) -> None:
        service = ContraindicationService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin", dose="5mg"),
            make_medication(drug_name="Warfarin", dose="10mg"),
        )
        issues = service.detect_duplicate_therapy(medications)
        assert len(issues) == 1


class TestDetectContraindications:
    def test_returns_empty_when_port_has_no_data(self) -> None:
        service = ContraindicationService(port=FakeMedicationSafetyPort())
        assert service.detect_contraindications((make_medication(),)) == ()

    def test_collects_contraindications_from_every_medication(self) -> None:
        port = FakeMedicationSafetyPort(contraindication="Do not use with nitrates.")
        service = ContraindicationService(port=port)

        contraindications = service.detect_contraindications(
            (make_medication(drug_name="A"), make_medication(drug_name="B"))
        )

        assert contraindications == ("Do not use with nitrates.", "Do not use with nitrates.")


class TestDetectBlackBoxWarnings:
    def test_returns_empty_when_port_has_no_data(self) -> None:
        service = ContraindicationService(port=FakeMedicationSafetyPort())
        assert service.detect_black_box_warnings((make_medication(),)) == ()

    def test_collects_warnings_from_every_medication(self) -> None:
        port = FakeMedicationSafetyPort(black_box_warning="Bleeding risk.")
        service = ContraindicationService(port=port)

        warnings = service.detect_black_box_warnings((make_medication(),))

        assert warnings == ("Bleeding risk.",)
