"""Unit tests for the `Insurance` aggregate's invariants."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.domain.entities import Insurance
from app.modules.patient.domain.enums import InsuranceStatus
from app.modules.patient.domain.events import (
    InsuranceAdded,
    InsuranceStatusChanged,
    InsuranceUpdated,
)
from app.modules.patient.domain.exceptions import (
    InsurancePolicyNumberRequiredError,
    InsuranceProviderNameRequiredError,
    InvalidInsuranceDateRangeError,
)


def _make_insurance(**overrides: object) -> Insurance:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "provider_name": "Acme Health",
        "policy_number": "POL-001",
        "effective_date": date(2026, 1, 1),
        "expiry_date": date(2027, 1, 1),
    }
    defaults.update(overrides)
    return Insurance.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_insurance_added_event(self) -> None:
        patient_id = uuid4()
        insurance = _make_insurance(patient_id=patient_id)

        assert insurance.patient_id == patient_id
        assert insurance.status is InsuranceStatus.ACTIVE
        events = insurance.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], InsuranceAdded)
        assert events[0].policy_number == "POL-001"

    def test_blank_provider_name_is_rejected(self) -> None:
        with pytest.raises(InsuranceProviderNameRequiredError):
            _make_insurance(provider_name="   ")

    def test_blank_policy_number_is_rejected(self) -> None:
        with pytest.raises(InsurancePolicyNumberRequiredError):
            _make_insurance(policy_number="   ")

    def test_expiry_before_effective_is_rejected(self) -> None:
        with pytest.raises(InvalidInsuranceDateRangeError):
            _make_insurance(effective_date=date(2027, 1, 1), expiry_date=date(2026, 1, 1))

    def test_expiry_equal_to_effective_is_rejected(self) -> None:
        with pytest.raises(InvalidInsuranceDateRangeError):
            _make_insurance(effective_date=date(2026, 1, 1), expiry_date=date(2026, 1, 1))


class TestIsExpired:
    def test_is_expired_true_after_expiry_date(self) -> None:
        insurance = _make_insurance(effective_date=date(2020, 1, 1), expiry_date=date(2021, 1, 1))
        assert insurance.is_expired(today=date(2022, 1, 1)) is True

    def test_is_expired_false_before_expiry_date(self) -> None:
        insurance = _make_insurance(effective_date=date(2020, 1, 1), expiry_date=date(2030, 1, 1))
        assert insurance.is_expired(today=date(2022, 1, 1)) is False


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        insurance = _make_insurance()
        insurance.pull_events()

        insurance.update_details(provider_name="New Provider", member_id="M-123")

        assert insurance.provider_name == "New Provider"
        assert insurance.member_id == "M-123"
        events = insurance.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], InsuranceUpdated)

    def test_update_rejects_blank_provider_name(self) -> None:
        insurance = _make_insurance()
        with pytest.raises(InsuranceProviderNameRequiredError):
            insurance.update_details(provider_name="   ")

    def test_update_validates_new_date_range_against_existing_dates(self) -> None:
        insurance = _make_insurance(effective_date=date(2026, 1, 1), expiry_date=date(2027, 1, 1))
        with pytest.raises(InvalidInsuranceDateRangeError):
            insurance.update_details(expiry_date=date(2025, 1, 1))

    def test_update_allows_moving_both_dates_together(self) -> None:
        insurance = _make_insurance(effective_date=date(2026, 1, 1), expiry_date=date(2027, 1, 1))
        insurance.update_details(effective_date=date(2028, 1, 1), expiry_date=date(2029, 1, 1))
        assert insurance.effective_date == date(2028, 1, 1)
        assert insurance.expiry_date == date(2029, 1, 1)


class TestStatusTransitions:
    def test_deactivate_then_activate_round_trips(self) -> None:
        insurance = _make_insurance()
        insurance.pull_events()

        insurance.deactivate()
        assert insurance.status is InsuranceStatus.INACTIVE
        events = insurance.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], InsuranceStatusChanged)

        insurance.activate()
        assert insurance.status is InsuranceStatus.ACTIVE

    def test_cancel_records_event(self) -> None:
        insurance = _make_insurance()
        insurance.pull_events()

        insurance.cancel()
        assert insurance.status is InsuranceStatus.CANCELLED
        events = insurance.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], InsuranceStatusChanged)

    def test_activating_an_already_active_insurance_is_idempotent(self) -> None:
        insurance = _make_insurance()
        insurance.pull_events()
        insurance.activate()
        assert insurance.pull_events() == []
