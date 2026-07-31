"""Unit tests for the `ArchiveMedicalDocument` use case (Active ->
Archived)."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.documents.application.dto import ArchiveMedicalDocumentInput
from app.modules.documents.application.use_cases.archive_medical_document import (
    ArchiveMedicalDocument,
)
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider
from app.modules.documents.domain.exceptions import (
    InvalidDocumentStatusTransitionError,
    MedicalDocumentNotFoundError,
)
from app.modules.documents.domain.value_objects import Sha256Checksum
from tests.unit.modules.documents.application.fakes import (
    FakeMedicalDocumentRepository,
    FakeUnitOfWork,
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
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


class TestArchiveMedicalDocument:
    async def test_archives_an_active_document(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        document = _make_document()
        document.activate()
        await document_repository.add(document)
        use_case = ArchiveMedicalDocument(
            document_repository=document_repository, unit_of_work=unit_of_work
        )

        output = await use_case.execute(ArchiveMedicalDocumentInput(document_id=document.id))

        assert output.status is DocumentStatus.ARCHIVED
        stored = await document_repository.get_by_id(document.id)
        assert stored is not None
        assert stored.status is DocumentStatus.ARCHIVED
        assert unit_of_work.committed is True

    async def test_unknown_document_raises(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = ArchiveMedicalDocument(
            document_repository=document_repository, unit_of_work=unit_of_work
        )
        with pytest.raises(MedicalDocumentNotFoundError):
            await use_case.execute(ArchiveMedicalDocumentInput(document_id=uuid4()))

    async def test_archiving_a_document_still_uploading_is_rejected(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        document = _make_document()
        await document_repository.add(document)
        use_case = ArchiveMedicalDocument(
            document_repository=document_repository, unit_of_work=unit_of_work
        )

        with pytest.raises(InvalidDocumentStatusTransitionError):
            await use_case.execute(ArchiveMedicalDocumentInput(document_id=document.id))
