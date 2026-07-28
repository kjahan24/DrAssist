"""Unit tests for the `PatientMedicalCondition` aggregate's invariants."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.domain.entities import PatientMedicalCondition
from app.modules.patient.domain.enums import ConditionSeverity, ConditionStatus
from app.modules.patient.domain.events import (
    PatientMedicalConditionReactivated,
    PatientMedicalConditionRecorded,
    PatientMedicalConditionResolved,
    PatientMedicalConditionUpdated,
)
from app.modules.patient.domain.exceptions import (
    ConditionCategoryRequiredError,
    ConditionNameRequiredError,
    InvalidResolvedDateError,
    ResolvedDateRequiredForChronicConditionError,
)
from app.modules.patient.domain.value_objects import ICD10Code


def _make_condition(**overrides: object) -> PatientMedicalCondition:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "condition_name": "Type 2 Diabetes",
        "category": "Endocrine",
        "severity": ConditionSeverity.MODERATE,
        "diagnosis_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return PatientMedicalCondition.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_patient_medical_condition_recorded_event(self) -> None:
        patient_id = uuid4()
        condition = _make_condition(patient_id=patient_id)

        assert condition.patient_id == patient_id
        assert condition.status is ConditionStatus.ACTIVE
        assert condition.is_chronic is False
        assert condition.is_infectious is False
        events = condition.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicalConditionRecorded)
        assert events[0].condition_name == "Type 2 Diabetes"

    def test_blank_condition_name_is_rejected(self) -> None:
        with pytest.raises(ConditionNameRequiredError):
            _make_condition(condition_name="   ")

    def test_blank_category_is_rejected(self) -> None:
        with pytest.raises(ConditionCategoryRequiredError):
            _make_condition(category="   ")

    def test_condition_name_and_category_are_stripped(self) -> None:
        condition = _make_condition(condition_name="  Asthma  ", category="  Respiratory  ")
        assert condition.condition_name == "Asthma"
        assert condition.category == "Respiratory"

    def test_icd10_code_is_optional(self) -> None:
        condition = _make_condition()
        assert condition.icd10_code is None

    def test_icd10_code_is_stored_as_value_object(self) -> None:
        condition = _make_condition(icd10_code=ICD10Code("E11.9"))
        assert str(condition.icd10_code) == "E11.9"

    def test_resolved_date_before_diagnosis_date_is_rejected(self) -> None:
        with pytest.raises(InvalidResolvedDateError):
            _make_condition(
                diagnosis_date=date(2026, 1, 10),
                status=ConditionStatus.RESOLVED,
                resolved_date=date(2026, 1, 1),
            )

    def test_resolved_date_equal_to_diagnosis_date_is_rejected(self) -> None:
        with pytest.raises(InvalidResolvedDateError):
            _make_condition(
                diagnosis_date=date(2026, 1, 1),
                status=ConditionStatus.RESOLVED,
                resolved_date=date(2026, 1, 1),
            )

    def test_resolved_date_after_diagnosis_date_is_accepted(self) -> None:
        condition = _make_condition(
            diagnosis_date=date(2026, 1, 1),
            status=ConditionStatus.RESOLVED,
            resolved_date=date(2026, 1, 10),
        )
        assert condition.resolved_date == date(2026, 1, 10)

    def test_chronic_and_resolved_without_resolved_date_is_rejected(self) -> None:
        with pytest.raises(ResolvedDateRequiredForChronicConditionError):
            _make_condition(is_chronic=True, status=ConditionStatus.RESOLVED, resolved_date=None)

    def test_chronic_and_resolved_with_resolved_date_is_accepted(self) -> None:
        condition = _make_condition(
            diagnosis_date=date(2026, 1, 1),
            is_chronic=True,
            status=ConditionStatus.RESOLVED,
            resolved_date=date(2026, 2, 1),
        )
        assert condition.resolved_date == date(2026, 2, 1)

    def test_not_chronic_and_resolved_without_resolved_date_is_accepted(self) -> None:
        condition = _make_condition(
            is_chronic=False, status=ConditionStatus.RESOLVED, resolved_date=None
        )
        assert condition.resolved_date is None


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        condition = _make_condition()
        condition.pull_events()

        condition.update_details(severity=ConditionSeverity.SEVERE, notes="Worsening")

        assert condition.severity is ConditionSeverity.SEVERE
        assert condition.notes == "Worsening"
        events = condition.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicalConditionUpdated)

    def test_update_rejects_blank_condition_name(self) -> None:
        condition = _make_condition()
        with pytest.raises(ConditionNameRequiredError):
            condition.update_details(condition_name="   ")

    def test_update_rejects_blank_category(self) -> None:
        condition = _make_condition()
        with pytest.raises(ConditionCategoryRequiredError):
            condition.update_details(category="   ")

    def test_update_diagnosis_date_revalidates_against_existing_resolved_date(self) -> None:
        condition = _make_condition(
            diagnosis_date=date(2026, 1, 1),
            status=ConditionStatus.RESOLVED,
            resolved_date=date(2026, 1, 10),
        )
        with pytest.raises(InvalidResolvedDateError):
            condition.update_details(diagnosis_date=date(2026, 2, 1))

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        condition = _make_condition(is_infectious=True)
        condition.update_details(notes="Follow-up needed")
        assert condition.is_infectious is True


class TestResolveAndReactivate:
    def test_resolve_sets_fields_and_records_event(self) -> None:
        condition = _make_condition(diagnosis_date=date(2026, 1, 1))
        condition.pull_events()

        condition.resolve(resolved_date=date(2026, 1, 20))

        assert condition.status is ConditionStatus.RESOLVED
        assert condition.resolved_date == date(2026, 1, 20)
        events = condition.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicalConditionResolved)
        assert events[0].resolved_date == date(2026, 1, 20)

    def test_resolve_rejects_resolved_date_not_after_diagnosis_date(self) -> None:
        condition = _make_condition(diagnosis_date=date(2026, 1, 10))
        with pytest.raises(InvalidResolvedDateError):
            condition.resolve(resolved_date=date(2026, 1, 1))

    def test_reactivate_resets_fields_and_records_event(self) -> None:
        condition = _make_condition(diagnosis_date=date(2026, 1, 1))
        condition.resolve(resolved_date=date(2026, 1, 20))
        condition.pull_events()

        condition.reactivate()

        assert condition.status is ConditionStatus.ACTIVE
        assert condition.resolved_date is None
        events = condition.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicalConditionReactivated)

    def test_reactivating_an_already_active_condition_is_idempotent(self) -> None:
        condition = _make_condition()
        condition.pull_events()
        condition.reactivate()
        assert condition.pull_events() == []
