"""Unit tests for the `MedicalDocument` aggregate's invariants, including
the strict `Uploading -> Active -> Archived -> Deleted` status chain."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider
from app.modules.documents.domain.events import (
    MedicalDocumentStatusChanged,
    MedicalDocumentUpdated,
    MedicalDocumentUploaded,
)
from app.modules.documents.domain.exceptions import (
    ExtensionRequiredError,
    InvalidDocumentStatusTransitionError,
    MimeTypeRequiredError,
    NonPositiveFileSizeError,
    OriginalFilenameRequiredError,
    StoragePathRequiredError,
    StoredFilenameRequiredError,
    TitleRequiredError,
)
from app.modules.documents.domain.value_objects import Sha256Checksum

_VALID_CHECKSUM = Sha256Checksum("a" * 64)


def _make_document(**overrides: object) -> MedicalDocument:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "uploaded_by_user_id": uuid4(),
        "category": DocumentCategory.LAB_REPORT,
        "title": "CBC Panel",
        "original_filename": "cbc-panel.pdf",
        "stored_filename": f"{uuid4().hex}.pdf",
        "mime_type": "application/pdf",
        "extension": ".pdf",
        "file_size_bytes": 20480,
        "storage_provider": StorageProvider.LOCAL,
        "storage_path": f"medical-documents/{uuid4().hex}.pdf",
        "checksum_sha256": _VALID_CHECKSUM,
        "uploaded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return MedicalDocument.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_medical_document_uploaded_event(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        document = _make_document(organization_id=organization_id, patient_id=patient_id)

        assert document.organization_id == organization_id
        assert document.patient_id == patient_id
        assert document.status is DocumentStatus.UPLOADING
        events = document.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], MedicalDocumentUploaded)

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(TitleRequiredError):
            _make_document(title="   ")

    def test_title_is_stripped(self) -> None:
        document = _make_document(title="  CBC Panel  ")
        assert document.title == "CBC Panel"

    def test_blank_original_filename_is_rejected(self) -> None:
        with pytest.raises(OriginalFilenameRequiredError):
            _make_document(original_filename="   ")

    def test_blank_stored_filename_is_rejected(self) -> None:
        with pytest.raises(StoredFilenameRequiredError):
            _make_document(stored_filename="   ")

    def test_blank_mime_type_is_rejected(self) -> None:
        with pytest.raises(MimeTypeRequiredError):
            _make_document(mime_type="   ")

    def test_blank_extension_is_rejected(self) -> None:
        with pytest.raises(ExtensionRequiredError):
            _make_document(extension="   ")

    def test_blank_storage_path_is_rejected(self) -> None:
        with pytest.raises(StoragePathRequiredError):
            _make_document(storage_path="   ")

    @pytest.mark.parametrize("value", [0, -1])
    def test_non_positive_file_size_is_rejected(self, value: int) -> None:
        with pytest.raises(NonPositiveFileSizeError):
            _make_document(file_size_bytes=value)

    def test_default_visit_and_appointment_are_none(self) -> None:
        document = _make_document()
        assert document.visit_id is None
        assert document.appointment_id is None

    def test_checksum_is_stored(self) -> None:
        document = _make_document()
        assert document.checksum_sha256 == _VALID_CHECKSUM


class TestStatusTransitions:
    def test_activate_moves_uploading_to_active(self) -> None:
        document = _make_document()
        document.pull_events()

        document.activate()

        assert document.status is DocumentStatus.ACTIVE
        events = document.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], MedicalDocumentStatusChanged)

    def test_archive_moves_active_to_archived(self) -> None:
        document = _make_document()
        document.activate()

        document.archive()

        assert document.status is DocumentStatus.ARCHIVED

    def test_soft_delete_moves_archived_to_deleted(self) -> None:
        document = _make_document()
        document.activate()
        document.archive()

        document.soft_delete()

        assert document.status is DocumentStatus.DELETED

    def test_archive_before_activate_is_rejected(self) -> None:
        document = _make_document()
        with pytest.raises(InvalidDocumentStatusTransitionError):
            document.archive()

    def test_soft_delete_before_archive_is_rejected(self) -> None:
        document = _make_document()
        document.activate()
        with pytest.raises(InvalidDocumentStatusTransitionError):
            document.soft_delete()

    def test_activate_twice_is_rejected(self) -> None:
        document = _make_document()
        document.activate()
        with pytest.raises(InvalidDocumentStatusTransitionError):
            document.activate()

    def test_transition_after_deleted_is_rejected(self) -> None:
        document = _make_document()
        document.activate()
        document.archive()
        document.soft_delete()
        with pytest.raises(InvalidDocumentStatusTransitionError):
            document.archive()


class TestUpdateDetails:
    def test_update_changes_title_description_tags_category_and_records_event(self) -> None:
        document = _make_document()
        document.pull_events()

        document.update_details(
            title="Updated Title",
            description="Follow-up notes",
            tags=["urgent", "follow-up"],
            category=DocumentCategory.CLINICAL_NOTE,
        )

        assert document.title == "Updated Title"
        assert document.description == "Follow-up notes"
        assert document.tags == ["urgent", "follow-up"]
        assert document.category is DocumentCategory.CLINICAL_NOTE
        events = document.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], MedicalDocumentUpdated)

    def test_update_without_fields_leaves_them_unchanged(self) -> None:
        document = _make_document(title="Original Title", description="Original description")
        document.update_details()
        assert document.title == "Original Title"
        assert document.description == "Original description"

    def test_update_with_blank_title_is_rejected(self) -> None:
        document = _make_document()
        with pytest.raises(TitleRequiredError):
            document.update_details(title="   ")

    def test_original_filename_and_storage_fields_are_immutable(self) -> None:
        """`update_details()` accepts no parameter for `original_filename`/
        `stored_filename`/`storage_path`/`checksum_sha256` at all — this
        test documents that omission is deliberate (see the module
        docstring in `domain/entities.py`), not an oversight."""
        document = _make_document()
        original_filename = document.original_filename
        storage_path = document.storage_path

        document.update_details(title="New Title")

        assert document.original_filename == original_filename
        assert document.storage_path == storage_path
