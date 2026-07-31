"""Unit tests for the `UpdateMedicalDocumentDetails` use case."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.documents.application.dto import UpdateMedicalDocumentDetailsInput
from app.modules.documents.application.use_cases.update_medical_document_details import (
    UpdateMedicalDocumentDetails,
)
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, StorageProvider
from app.modules.documents.domain.exceptions import MedicalDocumentNotFoundError
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


class TestUpdateMedicalDocumentDetails:
    async def test_updates_title_description_tags_and_category(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        document = _make_document()
        await document_repository.add(document)
        use_case = UpdateMedicalDocumentDetails(
            document_repository=document_repository, unit_of_work=unit_of_work
        )

        await use_case.execute(
            UpdateMedicalDocumentDetailsInput(
                document_id=document.id,
                title="Updated Title",
                description="Follow-up notes",
                tags=["urgent"],
                category=DocumentCategory.CLINICAL_NOTE,
            )
        )

        stored = await document_repository.get_by_id(document.id)
        assert stored is not None
        assert stored.title == "Updated Title"
        assert stored.description == "Follow-up notes"
        assert stored.tags == ["urgent"]
        assert stored.category is DocumentCategory.CLINICAL_NOTE
        assert unit_of_work.committed is True

    async def test_unknown_document_raises(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = UpdateMedicalDocumentDetails(
            document_repository=document_repository, unit_of_work=unit_of_work
        )
        with pytest.raises(MedicalDocumentNotFoundError):
            await use_case.execute(UpdateMedicalDocumentDetailsInput(document_id=uuid4()))
