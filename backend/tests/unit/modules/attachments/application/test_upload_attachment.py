"""Unit tests for the `UploadVisitAttachment` use case, using in-memory
fakes for both this module's own repository and the Visit/Doctor
modules' public ports."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.attachments.application.dto import UploadVisitAttachmentInput
from app.modules.attachments.application.use_cases.upload_attachment import (
    UploadVisitAttachment,
)
from app.modules.attachments.domain.enums import AttachmentType, StorageProvider
from app.modules.attachments.domain.events import VisitAttachmentUploaded
from app.modules.attachments.domain.exceptions import (
    DuplicateChecksumError,
    DuplicateStorageKeyError,
)
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.visit.domain.exceptions import PatientVisitNotFoundError
from tests.unit.modules.attachments.application.fakes import (
    FakeDoctorQueryPort,
    FakeUnitOfWork,
    FakeVisitAttachmentRepository,
    FakeVisitQueryPort,
)

_VALID_CHECKSUM = "a" * 64


def _make_input(**overrides: object) -> UploadVisitAttachmentInput:
    defaults: dict[str, object] = {
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
    return UploadVisitAttachmentInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def attachment_repository() -> FakeVisitAttachmentRepository:
    return FakeVisitAttachmentRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    attachment_repository: FakeVisitAttachmentRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_visits: dict[object, object] | None = None,
    existing_doctors: dict[object, object] | None = None,
) -> UploadVisitAttachment:
    return UploadVisitAttachment(
        attachment_repository=attachment_repository,
        visit_query_port=FakeVisitQueryPort(existing_visits=existing_visits),  # type: ignore[arg-type]
        doctor_query_port=FakeDoctorQueryPort(existing_doctors=existing_doctors),  # type: ignore[arg-type]
        unit_of_work=unit_of_work,
    )


class TestUploadVisitAttachment:
    async def test_uploads_an_attachment_for_an_existing_visit(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            attachment_repository, unit_of_work, existing_visits={visit_id: organization_id}
        )

        output = await use_case.execute(_make_input(visit_id=visit_id))

        stored = await attachment_repository.get_by_id(output.attachment_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, VisitAttachmentUploaded) for e in unit_of_work.published_events)

    async def test_unknown_visit_raises(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(attachment_repository, unit_of_work)

        with pytest.raises(PatientVisitNotFoundError):
            await use_case.execute(_make_input(visit_id=uuid4()))

    async def test_uploaded_by_with_unknown_doctor_raises(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            attachment_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, uploaded_by=uuid4()))

    async def test_uploaded_by_doctor_from_a_different_organization_raises(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        visit_organization_id = uuid4()
        doctor_organization_id = uuid4()
        use_case = _use_case(
            attachment_repository,
            unit_of_work,
            existing_visits={visit_id: visit_organization_id},
            existing_doctors={doctor_id: doctor_organization_id},
        )

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(visit_id=visit_id, uploaded_by=doctor_id))

    async def test_uploaded_by_doctor_in_the_same_organization_is_accepted(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        doctor_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            attachment_repository,
            unit_of_work,
            existing_visits={visit_id: organization_id},
            existing_doctors={doctor_id: organization_id},
        )

        output = await use_case.execute(_make_input(visit_id=visit_id, uploaded_by=doctor_id))

        stored = await attachment_repository.get_by_id(output.attachment_id)
        assert stored is not None
        assert stored.uploaded_by == doctor_id

    async def test_duplicate_storage_key_is_rejected(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_id = uuid4()
        use_case = _use_case(
            attachment_repository, unit_of_work, existing_visits={visit_id: uuid4()}
        )
        storage_key = "visits/shared/scan.png"

        await use_case.execute(
            _make_input(visit_id=visit_id, storage_key=storage_key, checksum_sha256="a" * 64)
        )

        with pytest.raises(DuplicateStorageKeyError):
            await use_case.execute(
                _make_input(visit_id=visit_id, storage_key=storage_key, checksum_sha256="b" * 64)
            )

    async def test_duplicate_checksum_is_rejected_even_across_different_visits(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_a = uuid4()
        visit_b = uuid4()
        use_case = _use_case(
            attachment_repository,
            unit_of_work,
            existing_visits={visit_a: uuid4(), visit_b: uuid4()},
        )

        await use_case.execute(
            _make_input(
                visit_id=visit_a,
                storage_key="visits/a/scan.png",
                checksum_sha256="c" * 64,
            )
        )

        with pytest.raises(DuplicateChecksumError):
            await use_case.execute(
                _make_input(
                    visit_id=visit_b,
                    storage_key="visits/b/scan.png",
                    checksum_sha256="c" * 64,
                )
            )

    async def test_distinct_storage_key_and_checksum_on_different_visits_is_allowed(
        self,
        attachment_repository: FakeVisitAttachmentRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        visit_a = uuid4()
        visit_b = uuid4()
        use_case = _use_case(
            attachment_repository,
            unit_of_work,
            existing_visits={visit_a: uuid4(), visit_b: uuid4()},
        )

        await use_case.execute(
            _make_input(visit_id=visit_a, storage_key="visits/a/scan.png", checksum_sha256="d" * 64)
        )
        output_b = await use_case.execute(
            _make_input(visit_id=visit_b, storage_key="visits/b/scan.png", checksum_sha256="e" * 64)
        )

        stored_b = await attachment_repository.get_by_id(output_b.attachment_id)
        assert stored_b is not None
        assert stored_b.visit_id == visit_b
