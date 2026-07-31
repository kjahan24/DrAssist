"""Unit tests for `MedicalDocumentQueryService` — backs the module's
public `DocumentQueryPort` facade."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.documents.application.services.document_query_service import (
    MedicalDocumentQueryService,
)
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, StorageProvider
from app.modules.documents.domain.value_objects import Sha256Checksum
from tests.unit.modules.documents.application.fakes import FakeMedicalDocumentRepository


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
        "checksum_sha256": Sha256Checksum(uuid4().hex + uuid4().hex[:32]),
        "uploaded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return MedicalDocument.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def document_repo() -> FakeMedicalDocumentRepository:
    return FakeMedicalDocumentRepository()


@pytest.fixture
def service(document_repo: FakeMedicalDocumentRepository) -> MedicalDocumentQueryService:
    return MedicalDocumentQueryService(document_repository=document_repo)


class TestDocumentExists:
    async def test_true_for_a_known_document(
        self,
        service: MedicalDocumentQueryService,
        document_repo: FakeMedicalDocumentRepository,
    ) -> None:
        document = _make_document()
        await document_repo.add(document)
        assert await service.document_exists(document.id) is True

    async def test_false_for_an_unknown_document(
        self, service: MedicalDocumentQueryService
    ) -> None:
        assert await service.document_exists(uuid4()) is False


class TestGetDocumentSummary:
    async def test_returns_none_for_an_unknown_document(
        self, service: MedicalDocumentQueryService
    ) -> None:
        assert await service.get_document_summary(uuid4()) is None

    async def test_returns_a_matching_summary(
        self,
        service: MedicalDocumentQueryService,
        document_repo: FakeMedicalDocumentRepository,
    ) -> None:
        document = _make_document(title="Chest X-Ray")
        await document_repo.add(document)

        summary = await service.get_document_summary(document.id)

        assert summary is not None
        assert summary.id == document.id
        assert summary.title == "Chest X-Ray"
        assert summary.checksum_sha256 == str(document.checksum_sha256)


class TestListDocumentsForPatient:
    async def test_returns_documents_ordered_by_uploaded_at_descending(
        self,
        service: MedicalDocumentQueryService,
        document_repo: FakeMedicalDocumentRepository,
    ) -> None:
        patient_id = uuid4()
        earlier = datetime(2026, 1, 1, 9, 0)
        later = earlier + timedelta(hours=1)
        await document_repo.add(
            _make_document(patient_id=patient_id, title="earlier", uploaded_at=earlier)
        )
        await document_repo.add(
            _make_document(patient_id=patient_id, title="later", uploaded_at=later)
        )

        summaries = await service.list_documents_for_patient(patient_id)

        assert [s.title for s in summaries] == ["later", "earlier"]

    async def test_returns_empty_list_for_a_patient_without_documents(
        self, service: MedicalDocumentQueryService
    ) -> None:
        assert await service.list_documents_for_patient(uuid4()) == []
