"""Unit tests for the `VisitAttachment` aggregate's invariants."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.enums import AttachmentType, StorageProvider
from app.modules.attachments.domain.events import (
    VisitAttachmentUpdated,
    VisitAttachmentUploaded,
)
from app.modules.attachments.domain.exceptions import (
    FileNameRequiredError,
    MimeTypeRequiredError,
    NonPositiveFileSizeError,
    OriginalFileNameRequiredError,
    StorageBucketRequiredError,
    StorageKeyRequiredError,
)
from app.modules.attachments.domain.value_objects import Sha256Checksum

_VALID_CHECKSUM = Sha256Checksum("a" * 64)


def _make_attachment(**overrides: object) -> VisitAttachment:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "attachment_type": AttachmentType.IMAGE,
        "file_name": "scan-001.png",
        "original_file_name": "chest-xray.png",
        "mime_type": "image/png",
        "file_size_bytes": 2048,
        "storage_provider": StorageProvider.S3,
        "storage_bucket": "drassist-attachments",
        "storage_key": f"visits/{uuid4()}/scan-001.png",
        "checksum_sha256": _VALID_CHECKSUM,
        "uploaded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitAttachment.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_visit_attachment_uploaded_event(self) -> None:
        organization_id = uuid4()
        visit_id = uuid4()
        attachment = _make_attachment(organization_id=organization_id, visit_id=visit_id)

        assert attachment.organization_id == organization_id
        assert attachment.visit_id == visit_id
        events = attachment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitAttachmentUploaded)

    def test_blank_file_name_is_rejected(self) -> None:
        with pytest.raises(FileNameRequiredError):
            _make_attachment(file_name="   ")

    def test_file_name_is_stripped(self) -> None:
        attachment = _make_attachment(file_name="  scan.png  ")
        assert attachment.file_name == "scan.png"

    def test_blank_original_file_name_is_rejected(self) -> None:
        with pytest.raises(OriginalFileNameRequiredError):
            _make_attachment(original_file_name="   ")

    def test_original_file_name_is_stripped(self) -> None:
        attachment = _make_attachment(original_file_name="  xray.png  ")
        assert attachment.original_file_name == "xray.png"

    def test_blank_mime_type_is_rejected(self) -> None:
        with pytest.raises(MimeTypeRequiredError):
            _make_attachment(mime_type="   ")

    def test_mime_type_is_stripped(self) -> None:
        attachment = _make_attachment(mime_type="  image/png  ")
        assert attachment.mime_type == "image/png"

    def test_blank_storage_bucket_is_rejected(self) -> None:
        with pytest.raises(StorageBucketRequiredError):
            _make_attachment(storage_bucket="   ")

    def test_storage_bucket_is_stripped(self) -> None:
        attachment = _make_attachment(storage_bucket="  my-bucket  ")
        assert attachment.storage_bucket == "my-bucket"

    def test_blank_storage_key_is_rejected(self) -> None:
        with pytest.raises(StorageKeyRequiredError):
            _make_attachment(storage_key="   ")

    def test_storage_key_is_stripped(self) -> None:
        attachment = _make_attachment(storage_key="  visits/a/scan.png  ")
        assert attachment.storage_key == "visits/a/scan.png"

    @pytest.mark.parametrize("value", [0, -1])
    def test_non_positive_file_size_is_rejected(self, value: int) -> None:
        with pytest.raises(NonPositiveFileSizeError):
            _make_attachment(file_size_bytes=value)

    def test_positive_file_size_is_accepted(self) -> None:
        attachment = _make_attachment(file_size_bytes=1)
        assert attachment.file_size_bytes == 1

    def test_default_uploaded_by_is_none(self) -> None:
        attachment = _make_attachment()
        assert attachment.uploaded_by is None

    def test_default_description_is_none(self) -> None:
        attachment = _make_attachment()
        assert attachment.description is None

    def test_checksum_is_stored(self) -> None:
        attachment = _make_attachment()
        assert attachment.checksum_sha256 == _VALID_CHECKSUM


class TestUpdateDetails:
    def test_update_changes_description_and_records_event(self) -> None:
        attachment = _make_attachment()
        attachment.pull_events()

        attachment.update_details(description="Chest X-ray, follow-up")

        assert attachment.description == "Chest X-ray, follow-up"
        events = attachment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitAttachmentUpdated)

    def test_update_without_description_leaves_it_unchanged(self) -> None:
        attachment = _make_attachment(description="Original description")
        attachment.update_details()
        assert attachment.description == "Original description"
