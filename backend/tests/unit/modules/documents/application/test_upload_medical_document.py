"""Unit tests for the `UploadMedicalDocument` use case, using in-memory
fakes for this module's own repository/storage and the Patient/Visit/
Appointment modules' public ports."""

from io import BytesIO
from uuid import UUID, uuid4

import pytest

from app.modules.documents.application.dto import UploadMedicalDocumentInput
from app.modules.documents.application.use_cases import upload_medical_document as upload_module
from app.modules.documents.application.use_cases.upload_medical_document import (
    UploadMedicalDocument,
)
from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider
from app.modules.documents.domain.events import MedicalDocumentUploaded
from app.modules.documents.domain.exceptions import (
    AppointmentNotFoundError,
    AppointmentOwnershipMismatchError,
    DuplicateStoredFilenameError,
    PatientNotFoundError,
    VisitNotFoundError,
    VisitOwnershipMismatchError,
)
from tests.unit.modules.documents.application.fakes import (
    FakeAppointmentQueryPort,
    FakeMedicalDocumentRepository,
    FakePatientQueryPort,
    FakeStoragePort,
    FakeUnitOfWork,
    FakeVisitQueryPort,
)

_VALID_CHECKSUM = "a" * 64


def _make_input(**overrides: object) -> UploadMedicalDocumentInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "uploaded_by_user_id": uuid4(),
        "category": DocumentCategory.LAB_REPORT,
        "title": "CBC Panel",
        "original_filename": "cbc-panel.pdf",
        "mime_type": "application/pdf",
        "extension": ".pdf",
        "file_size_bytes": 2048,
        "checksum_sha256": _VALID_CHECKSUM,
        "file_data": BytesIO(b"%PDF-1.4 fake contents"),
    }
    defaults.update(overrides)
    return UploadMedicalDocumentInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def document_repository() -> FakeMedicalDocumentRepository:
    return FakeMedicalDocumentRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def storage() -> FakeStoragePort:
    return FakeStoragePort()


def _use_case(
    document_repository: FakeMedicalDocumentRepository,
    unit_of_work: FakeUnitOfWork,
    storage: FakeStoragePort,
    *,
    existing_patients: dict[UUID, UUID] | None = None,
    existing_visits: dict[UUID, tuple[UUID, UUID]] | None = None,
    existing_appointments: dict[UUID, tuple[UUID, UUID]] | None = None,
) -> UploadMedicalDocument:
    return UploadMedicalDocument(
        document_repository=document_repository,
        patient_query_port=FakePatientQueryPort(existing_patients=existing_patients),
        visit_query_port=FakeVisitQueryPort(existing_visits=existing_visits),
        appointment_query_port=FakeAppointmentQueryPort(
            existing_appointments=existing_appointments
        ),
        storage=storage,
        storage_provider=StorageProvider.LOCAL,
        unit_of_work=unit_of_work,
    )


class TestUploadMedicalDocument:
    async def test_uploads_a_document_for_an_existing_patient(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        patient_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: organization_id},
        )

        output = await use_case.execute(_make_input(patient_id=patient_id))

        stored = await document_repository.get_by_id(output.document_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.status is DocumentStatus.ACTIVE
        assert unit_of_work.committed is True
        assert any(isinstance(e, MedicalDocumentUploaded) for e in unit_of_work.published_events)
        assert storage.objects[("medical-documents", stored.stored_filename)] == (
            b"%PDF-1.4 fake contents"
        )

    async def test_unknown_patient_raises(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        use_case = _use_case(document_repository, unit_of_work, storage)

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(_make_input(patient_id=uuid4()))

    async def test_unknown_visit_raises(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        patient_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: uuid4()},
        )

        with pytest.raises(VisitNotFoundError):
            await use_case.execute(_make_input(patient_id=patient_id, visit_id=uuid4()))

    async def test_visit_belonging_to_a_different_patient_raises_ownership_mismatch(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        patient_id = uuid4()
        organization_id = uuid4()
        visit_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: organization_id},
            existing_visits={visit_id: (organization_id, uuid4())},
        )

        with pytest.raises(VisitOwnershipMismatchError):
            await use_case.execute(_make_input(patient_id=patient_id, visit_id=visit_id))

    async def test_visit_belonging_to_the_same_patient_is_accepted(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        patient_id = uuid4()
        organization_id = uuid4()
        visit_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: organization_id},
            existing_visits={visit_id: (organization_id, patient_id)},
        )

        output = await use_case.execute(_make_input(patient_id=patient_id, visit_id=visit_id))

        stored = await document_repository.get_by_id(output.document_id)
        assert stored is not None
        assert stored.visit_id == visit_id

    async def test_unknown_appointment_raises(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        patient_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: uuid4()},
        )

        with pytest.raises(AppointmentNotFoundError):
            await use_case.execute(_make_input(patient_id=patient_id, appointment_id=uuid4()))

    async def test_appointment_belonging_to_a_different_organization_raises_ownership_mismatch(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        patient_id = uuid4()
        organization_id = uuid4()
        appointment_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: organization_id},
            existing_appointments={appointment_id: (uuid4(), patient_id)},
        )

        with pytest.raises(AppointmentOwnershipMismatchError):
            await use_case.execute(
                _make_input(patient_id=patient_id, appointment_id=appointment_id)
            )

    async def test_duplicate_stored_filename_is_rejected(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        patient_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: uuid4()},
        )
        fixed_uuid = uuid4()
        monkeypatch.setattr(upload_module, "uuid4", lambda: fixed_uuid)

        await use_case.execute(_make_input(patient_id=patient_id))

        with pytest.raises(DuplicateStoredFilenameError):
            await use_case.execute(_make_input(patient_id=patient_id))

    async def test_stored_filename_preserves_the_extension(
        self,
        document_repository: FakeMedicalDocumentRepository,
        unit_of_work: FakeUnitOfWork,
        storage: FakeStoragePort,
    ) -> None:
        patient_id = uuid4()
        use_case = _use_case(
            document_repository,
            unit_of_work,
            storage,
            existing_patients={patient_id: uuid4()},
        )

        output = await use_case.execute(_make_input(patient_id=patient_id, extension=".pdf"))

        assert output.stored_filename.endswith(".pdf")
