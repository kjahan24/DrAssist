"""Unit tests for the `SOAPNote` aggregate.

No status/editability tests here — `SOAPNote` has no status field of its
own and `update_details()` performs no such check (see
`app/modules/soap_notes/domain/entities.py`); that guard is exercised at
the application layer in `test_update_soap_note.py` instead.
"""

from uuid import uuid4

from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.domain.events import SOAPNoteCreated, SOAPNoteUpdated


def _make_soap_note(**overrides: object) -> SOAPNote:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
    }
    defaults.update(overrides)
    return SOAPNote.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        clinical_note_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()

        soap_note = _make_soap_note(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )

        assert soap_note.organization_id == organization_id
        assert soap_note.clinical_note_id == clinical_note_id
        assert soap_note.patient_id == patient_id
        assert soap_note.visit_id == visit_id
        assert soap_note.doctor_id == doctor_id
        events = soap_note.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], SOAPNoteCreated)
        assert events[0].soap_note_id == soap_note.id
        assert events[0].clinical_note_id == clinical_note_id

    def test_all_seven_text_fields_default_to_none(self) -> None:
        soap_note = _make_soap_note()

        assert soap_note.chief_complaint is None
        assert soap_note.history_of_present_illness is None
        assert soap_note.review_of_systems is None
        assert soap_note.physical_examination is None
        assert soap_note.vital_sign_summary is None
        assert soap_note.assessment is None
        assert soap_note.plan is None

    def test_create_accepts_text_fields_up_front(self) -> None:
        soap_note = _make_soap_note(chief_complaint="Headache", assessment="Tension headache")

        assert soap_note.chief_complaint == "Headache"
        assert soap_note.assessment == "Tension headache"


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        soap_note = _make_soap_note()
        soap_note.pull_events()

        soap_note.update_details(chief_complaint="Chest pain", plan="Order ECG")

        assert soap_note.chief_complaint == "Chest pain"
        assert soap_note.plan == "Order ECG"
        events = soap_note.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], SOAPNoteUpdated)
        assert events[0].soap_note_id == soap_note.id
        assert events[0].clinical_note_id == soap_note.clinical_note_id

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        soap_note = _make_soap_note(assessment="Stable")

        soap_note.update_details(plan="Follow up in 2 weeks")

        assert soap_note.assessment == "Stable"
        assert soap_note.plan == "Follow up in 2 weeks"

    def test_update_touches_updated_at(self) -> None:
        soap_note = _make_soap_note()
        original_updated_at = soap_note.updated_at

        soap_note.update_details(assessment="Revised assessment")

        assert soap_note.updated_at >= original_updated_at

    def test_update_all_seven_fields_at_once(self) -> None:
        soap_note = _make_soap_note()

        soap_note.update_details(
            chief_complaint="Cough",
            history_of_present_illness="3 days of dry cough",
            review_of_systems="No fever",
            physical_examination="Clear lungs",
            vital_sign_summary="Temp 37.0C",
            assessment="Viral URI",
            plan="Supportive care",
        )

        assert soap_note.chief_complaint == "Cough"
        assert soap_note.history_of_present_illness == "3 days of dry cough"
        assert soap_note.review_of_systems == "No fever"
        assert soap_note.physical_examination == "Clear lungs"
        assert soap_note.vital_sign_summary == "Temp 37.0C"
        assert soap_note.assessment == "Viral URI"
        assert soap_note.plan == "Supportive care"
