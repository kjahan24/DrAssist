"""Unit tests for the `DownloadMedicalDocument` use case."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.documents.application.constants import DOCUMENT_STORAGE_BUCKET
from app.modules.documents.application.dto import DownloadMedicalDocumentInput
from app.modules.documents.application.use_cases.download_medical_document import (
    DownloadMedicalDocument,
)
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, StorageProvider
from app.modules.documents.domain.exceptions import MedicalDocumentNotFoundError
from app.modules.documents.domain.value_objects import Sha256Checksum
from tests.unit.modules.documents.application.fakes import (
    FakeMedicalDocumentRepository,
    FakeStoragePort,
)


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
        "file_size_bytes": 2048,
        "storage_provider": StorageProvider.LOCAL,
        "storage_path": f"medical-documents/{uuid4().hex}.pdf",
        "checksum_sha256": Sha256Checksum("a" * 64),
        "uploaded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return MedicalDocument.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def document_repository() -> FakeMedicalDocumentRepository:
    return FakeMedicalDocumentRepository()


@pytest.fixture
def storage() -> FakeStoragePort:
    return FakeStoragePort()


class TestDownloadMedicalDocument:
    async def test_downloads_the_stored_bytes(
        self,
        document_repository: FakeMedicalDocumentRepository,
        storage: FakeStoragePort,
    ) -> None:
        document = _make_document()
        await document_repository.add(document)
        storage.objects[(DOCUMENT_STORAGE_BUCKET, document.storage_path)] = b"file contents"
        use_case = DownloadMedicalDocument(document_repository=document_repository, storage=storage)

        output = await use_case.execute(DownloadMedicalDocumentInput(document_id=document.id))

        assert output.file_data == b"file contents"
        assert output.original_filename == document.original_filename
        assert output.mime_type == document.mime_type

    async def test_unknown_document_raises(
        self,
        document_repository: FakeMedicalDocumentRepository,
        storage: FakeStoragePort,
    ) -> None:
        use_case = DownloadMedicalDocument(document_repository=document_repository, storage=storage)
        with pytest.raises(MedicalDocumentNotFoundError):
            await use_case.execute(DownloadMedicalDocumentInput(document_id=uuid4()))
