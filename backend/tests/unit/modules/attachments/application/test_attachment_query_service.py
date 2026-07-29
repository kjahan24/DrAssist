"""Unit tests for `VisitAttachmentQueryService` — backs the module's
public `AttachmentQueryPort` facade."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.attachments.application.services.attachment_query_service import (
    VisitAttachmentQueryService,
)
from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.enums import AttachmentType, StorageProvider
from app.modules.attachments.domain.value_objects import Sha256Checksum
from tests.unit.modules.attachments.application.fakes import FakeVisitAttachmentRepository


def _make_attachment(**overrides: object) -> VisitAttachment:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "attachment_type": AttachmentType.IMAGE,
        "file_name": "scan.png",
        "original_file_name": "scan.png",
        "mime_type": "image/png",
        "file_size_bytes": 1024,
        "storage_provider": StorageProvider.S3,
        "storage_bucket": "drassist-attachments",
        "storage_key": f"visits/{uuid4()}/scan.png",
        "checksum_sha256": Sha256Checksum(uuid4().hex + uuid4().hex[:32]),
        "uploaded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitAttachment.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def attachment_repo() -> FakeVisitAttachmentRepository:
    return FakeVisitAttachmentRepository()


@pytest.fixture
def service(attachment_repo: FakeVisitAttachmentRepository) -> VisitAttachmentQueryService:
    return VisitAttachmentQueryService(attachment_repository=attachment_repo)


class TestAttachmentExists:
    async def test_true_for_a_known_attachment(
        self,
        service: VisitAttachmentQueryService,
        attachment_repo: FakeVisitAttachmentRepository,
    ) -> None:
        attachment = _make_attachment()
        await attachment_repo.add(attachment)
        assert await service.attachment_exists(attachment.id) is True

    async def test_false_for_an_unknown_attachment(
        self, service: VisitAttachmentQueryService
    ) -> None:
        assert await service.attachment_exists(uuid4()) is False


class TestListAttachmentsForVisit:
    async def test_returns_attachments_ordered_by_uploaded_at(
        self,
        service: VisitAttachmentQueryService,
        attachment_repo: FakeVisitAttachmentRepository,
    ) -> None:
        visit_id = uuid4()
        first_time = datetime(2026, 1, 1, 9, 0)
        second_time = first_time + timedelta(hours=1)
        await attachment_repo.add(
            _make_attachment(visit_id=visit_id, file_name="second.png", uploaded_at=second_time)
        )
        await attachment_repo.add(
            _make_attachment(visit_id=visit_id, file_name="first.png", uploaded_at=first_time)
        )

        summaries = await service.list_attachments_for_visit(visit_id)

        assert [s.file_name for s in summaries] == ["first.png", "second.png"]

    async def test_returns_empty_list_for_a_visit_without_attachments(
        self, service: VisitAttachmentQueryService
    ) -> None:
        assert await service.list_attachments_for_visit(uuid4()) == []
