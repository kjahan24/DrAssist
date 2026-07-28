"""Unit tests for the `DoctorLicense` aggregate's invariants."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.domain.entities import DoctorLicense
from app.modules.doctor.domain.enums import LicenseVerificationStatus
from app.modules.doctor.domain.events import (
    DoctorLicenseAdded,
    DoctorLicenseRejected,
    DoctorLicenseVerified,
)
from app.modules.doctor.domain.exceptions import (
    InvalidLicenseDateRangeError,
    LicenseNumberRequiredError,
)


def _make_license(**overrides: object) -> DoctorLicense:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "license_number": "LIC-12345",
        "issuing_authority": "Medical Council",
        "country": "USA",
        "issue_date": date(2020, 1, 1),
        "expiry_date": date(2030, 1, 1),
    }
    defaults.update(overrides)
    return DoctorLicense.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_license_added_event(self) -> None:
        doctor_id = uuid4()
        license_ = _make_license(doctor_id=doctor_id)

        assert license_.doctor_id == doctor_id
        assert license_.verification_status is LicenseVerificationStatus.PENDING
        events = license_.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorLicenseAdded)
        assert events[0].license_number == "LIC-12345"

    def test_blank_license_number_is_rejected(self) -> None:
        with pytest.raises(LicenseNumberRequiredError):
            _make_license(license_number="  ")

    def test_license_number_is_stripped(self) -> None:
        license_ = _make_license(license_number="  LIC-999  ")
        assert license_.license_number == "LIC-999"

    def test_expiry_before_issue_is_rejected(self) -> None:
        with pytest.raises(InvalidLicenseDateRangeError):
            _make_license(issue_date=date(2025, 1, 1), expiry_date=date(2024, 1, 1))

    def test_expiry_equal_to_issue_is_rejected(self) -> None:
        with pytest.raises(InvalidLicenseDateRangeError):
            _make_license(issue_date=date(2025, 1, 1), expiry_date=date(2025, 1, 1))


class TestIsExpired:
    def test_is_expired_true_after_expiry_date(self) -> None:
        license_ = _make_license(issue_date=date(2020, 1, 1), expiry_date=date(2021, 1, 1))
        assert license_.is_expired(today=date(2022, 1, 1)) is True

    def test_is_expired_false_before_expiry_date(self) -> None:
        license_ = _make_license(issue_date=date(2020, 1, 1), expiry_date=date(2030, 1, 1))
        assert license_.is_expired(today=date(2022, 1, 1)) is False


class TestVerificationTransitions:
    def test_verify_records_event(self) -> None:
        license_ = _make_license()
        license_.pull_events()

        license_.verify()
        assert license_.verification_status is LicenseVerificationStatus.VERIFIED
        events = license_.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorLicenseVerified)

    def test_reject_records_event(self) -> None:
        license_ = _make_license()
        license_.pull_events()

        license_.reject()
        assert license_.verification_status is LicenseVerificationStatus.REJECTED
        events = license_.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorLicenseRejected)

    def test_verifying_an_already_verified_license_is_idempotent(self) -> None:
        license_ = _make_license()
        license_.verify()
        license_.pull_events()
        license_.verify()
        assert license_.pull_events() == []
