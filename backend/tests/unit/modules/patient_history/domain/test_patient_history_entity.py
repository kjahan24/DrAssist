"""Unit tests for the `PatientHistory` aggregate's own invariants: it has
exactly one way its state is ever set (`create()`), `created_from_review`
is always `True`, and `summary` must be non-blank."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from app.modules.patient_history.domain.events import PatientHistoryCreated
from app.modules.patient_history.domain.exceptions import SummaryRequiredError


def _make_history(**overrides: object) -> PatientHistory:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_review_id": uuid4(),
        "history_type": HistoryType.DIAGNOSIS,
        "reference_type": ReferenceType.ICD10,
        "reference_id": uuid4(),
        "encounter_date": date(2026, 1, 1),
        "summary": "Community-acquired pneumonia, J18.9",
    }
    defaults.update(overrides)
    return PatientHistory.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_review_id = uuid4()
        reference_id = uuid4()

        history = _make_history(
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_review_id=doctor_review_id,
            reference_id=reference_id,
        )

        assert history.organization_id == organization_id
        assert history.patient_id == patient_id
        assert history.visit_id == visit_id
        assert history.doctor_review_id == doctor_review_id
        assert history.reference_id == reference_id
        events = history.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientHistoryCreated)
        assert events[0].patient_history_id == history.id
        assert events[0].patient_id == patient_id
        assert events[0].reference_id == reference_id

    def test_created_from_review_is_always_true(self) -> None:
        assert _make_history().created_from_review is True

    def test_history_type_and_reference_type_are_preserved(self) -> None:
        history = _make_history(
            history_type=HistoryType.MEDICATION, reference_type=ReferenceType.PRESCRIPTION
        )
        assert history.history_type is HistoryType.MEDICATION
        assert history.reference_type is ReferenceType.PRESCRIPTION

    def test_encounter_date_is_preserved(self) -> None:
        history = _make_history(encounter_date=date(2026, 3, 15))
        assert history.encounter_date == date(2026, 3, 15)

    def test_blank_summary_is_rejected(self) -> None:
        with pytest.raises(SummaryRequiredError):
            _make_history(summary="   ")

    def test_summary_is_stripped(self) -> None:
        history = _make_history(summary="  Pneumonia confirmed  ")
        assert history.summary == "Pneumonia confirmed"


class TestImmutability:
    def test_aggregate_exposes_no_mutator_beyond_create(self) -> None:
        """ "History records are immutable" / "append-only" — there is no
        `update_details()`, no status transition, nothing that could
        record a second event."""
        history = _make_history()
        public_methods = {
            name
            for name in dir(history)
            if not name.startswith("_")
            and callable(getattr(history, name))
            and name not in {"touch", "record_event", "pull_events", "create"}
        }
        assert public_methods == set()
