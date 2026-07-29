"""Unit tests for the `VisitDiagnosis` aggregate's invariants."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.diagnosis.domain.entities import VisitDiagnosis
from app.modules.diagnosis.domain.enums import DiagnosisStatus, DiagnosisType
from app.modules.diagnosis.domain.events import (
    VisitDiagnosisRecorded,
    VisitDiagnosisStatusChanged,
    VisitDiagnosisUpdated,
)
from app.modules.diagnosis.domain.exceptions import (
    DiagnosisNameRequiredError,
    InvalidSequenceNumberError,
    PrimaryDiagnosisCannotBeRuledOutError,
)


def _make_diagnosis(**overrides: object) -> VisitDiagnosis:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "sequence_number": 1,
        "diagnosis_name": "Type 2 diabetes",
        "diagnosis_type": DiagnosisType.PRIMARY,
        "diagnosed_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitDiagnosis.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_visit_diagnosis_recorded_event(self) -> None:
        organization_id = uuid4()
        visit_id = uuid4()
        diagnosis = _make_diagnosis(organization_id=organization_id, visit_id=visit_id)

        assert diagnosis.organization_id == organization_id
        assert diagnosis.visit_id == visit_id
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitDiagnosisRecorded)

    def test_blank_diagnosis_name_is_rejected(self) -> None:
        with pytest.raises(DiagnosisNameRequiredError):
            _make_diagnosis(diagnosis_name="   ")

    def test_diagnosis_name_is_stripped(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_name="  Hypertension  ")
        assert diagnosis.diagnosis_name == "Hypertension"

    @pytest.mark.parametrize("value", [0, -1])
    def test_sequence_number_below_one_is_rejected(self, value: int) -> None:
        with pytest.raises(InvalidSequenceNumberError):
            _make_diagnosis(sequence_number=value)

    def test_sequence_number_of_one_is_accepted(self) -> None:
        diagnosis = _make_diagnosis(sequence_number=1)
        assert diagnosis.sequence_number == 1

    def test_default_status_is_provisional(self) -> None:
        diagnosis = _make_diagnosis()
        assert diagnosis.diagnosis_status is DiagnosisStatus.PROVISIONAL

    def test_primary_ruled_out_at_creation_is_rejected(self) -> None:
        with pytest.raises(PrimaryDiagnosisCannotBeRuledOutError):
            _make_diagnosis(
                diagnosis_type=DiagnosisType.PRIMARY, diagnosis_status=DiagnosisStatus.RULED_OUT
            )

    def test_secondary_ruled_out_at_creation_is_accepted(self) -> None:
        diagnosis = _make_diagnosis(
            diagnosis_type=DiagnosisType.SECONDARY, diagnosis_status=DiagnosisStatus.RULED_OUT
        )
        assert diagnosis.diagnosis_status is DiagnosisStatus.RULED_OUT

    def test_icd10_code_is_optional(self) -> None:
        diagnosis = _make_diagnosis()
        assert diagnosis.icd10_code is None

    def test_icd10_code_is_stored_as_provided(self) -> None:
        diagnosis = _make_diagnosis(icd10_code="E11.9")
        assert diagnosis.icd10_code == "E11.9"


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.pull_events()

        diagnosis.update_details(clinical_notes="Diet-controlled")

        assert diagnosis.clinical_notes == "Diet-controlled"
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitDiagnosisUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        diagnosis = _make_diagnosis(icd10_code="E11.9")
        diagnosis.update_details(clinical_notes="Reviewed")
        assert diagnosis.icd10_code == "E11.9"

    def test_update_with_blank_diagnosis_name_is_rejected(self) -> None:
        diagnosis = _make_diagnosis()
        with pytest.raises(DiagnosisNameRequiredError):
            diagnosis.update_details(diagnosis_name="   ")


class TestConfirm:
    def test_confirm_sets_status_and_records_event(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_status=DiagnosisStatus.PROVISIONAL)
        diagnosis.pull_events()

        diagnosis.confirm()

        assert diagnosis.diagnosis_status is DiagnosisStatus.CONFIRMED
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitDiagnosisStatusChanged)
        assert events[0].status == "confirmed"

    def test_confirming_an_already_confirmed_diagnosis_is_idempotent(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_status=DiagnosisStatus.PROVISIONAL)
        diagnosis.confirm()
        diagnosis.pull_events()
        diagnosis.confirm()
        assert diagnosis.pull_events() == []


class TestRuleOut:
    def test_rule_out_sets_status_and_records_event_for_a_secondary_diagnosis(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_type=DiagnosisType.SECONDARY)
        diagnosis.pull_events()

        diagnosis.rule_out()

        assert diagnosis.diagnosis_status is DiagnosisStatus.RULED_OUT
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitDiagnosisStatusChanged)
        assert events[0].status == "ruled_out"

    def test_rule_out_on_a_primary_diagnosis_is_rejected(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_type=DiagnosisType.PRIMARY)
        with pytest.raises(PrimaryDiagnosisCannotBeRuledOutError):
            diagnosis.rule_out()

    def test_ruling_out_an_already_ruled_out_diagnosis_is_idempotent(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_type=DiagnosisType.DIFFERENTIAL)
        diagnosis.rule_out()
        diagnosis.pull_events()
        diagnosis.rule_out()
        assert diagnosis.pull_events() == []
