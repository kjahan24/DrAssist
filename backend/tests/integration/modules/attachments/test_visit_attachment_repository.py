"""Integration tests for `SqlAlchemyVisitAttachmentRepository`, including
the FKs to `organizations`/`patient_visits`/`doctors`, the global
`storage_key`/`checksum_sha256` uniqueness constraints, and the
`file_size_bytes` `CHECK` constraint, against a real PostgreSQL
instance."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.attachments._helpers import (
    persist_doctor,
    persist_organization,
    persist_patient,
    persist_visit,
)

from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.enums import AttachmentType, StorageProvider
from app.modules.attachments.domain.value_objects import Sha256Checksum
from app.modules.attachments.infrastructure.models import VisitAttachmentModel
from app.modules.attachments.infrastructure.repositories import (
    SqlAlchemyVisitAttachmentRepository,
)
from app.modules.doctor.domain.entities import Doctor
from app.modules.organization.domain.entities import Organization
from app.modules.patient.domain.entities import Patient
from app.modules.visit.domain.entities import PatientVisit


def _unique_checksum() -> str:
    return (uuid4().hex + uuid4().hex)[:64]


async def _persist_full_chain(
    db_session: AsyncSession,
) -> tuple[Organization, Patient, Doctor, PatientVisit]:
    organization = await persist_organization(db_session)
    patient = await persist_patient(db_session, organization_id=organization.id)
    doctor = await persist_doctor(db_session, organization_id=organization.id)
    visit = await persist_visit(
        db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
    )
    return organization, patient, doctor, visit


class TestVisitAttachmentRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, _patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitAttachmentRepository(db_session)
        checksum = Sha256Checksum(_unique_checksum())

        attachment = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit.id,
            attachment_type=AttachmentType.PDF,
            file_name="report-001.pdf",
            original_file_name="Lab Report.pdf",
            mime_type="application/pdf",
            file_size_bytes=51200,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=f"visits/{visit.id}/report-001.pdf",
            checksum_sha256=checksum,
            uploaded_by=doctor.id,
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            description="Lab results",
        )
        await repo.add(attachment)
        await db_session.commit()

        reloaded = await repo.get_by_id(attachment.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.visit_id == visit.id
        assert reloaded.attachment_type is AttachmentType.PDF
        assert reloaded.file_name == "report-001.pdf"
        assert reloaded.original_file_name == "Lab Report.pdf"
        assert reloaded.mime_type == "application/pdf"
        assert reloaded.file_size_bytes == 51200
        assert reloaded.storage_provider is StorageProvider.S3
        assert reloaded.storage_bucket == "drassist-attachments"
        assert reloaded.checksum_sha256 == checksum
        assert reloaded.uploaded_by == doctor.id
        assert reloaded.description == "Lab results"

    async def test_optional_fields_round_trip_as_none(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitAttachmentRepository(db_session)

        attachment = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="scan.png",
            original_file_name="scan.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.LOCAL,
            storage_bucket="local-storage",
            storage_key=f"visits/{visit.id}/scan.png",
            checksum_sha256=Sha256Checksum(_unique_checksum()),
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(attachment)
        await db_session.commit()

        reloaded = await repo.get_by_id(attachment.id)
        assert reloaded is not None
        assert reloaded.uploaded_by is None
        assert reloaded.description is None


class TestGetByStorageKey:
    async def test_returns_the_matching_attachment(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitAttachmentRepository(db_session)
        storage_key = f"visits/{visit.id}/scan.png"

        attachment = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="scan.png",
            original_file_name="scan.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=storage_key,
            checksum_sha256=Sha256Checksum(_unique_checksum()),
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(attachment)
        await db_session.commit()

        found = await repo.get_by_storage_key(storage_key)
        assert found is not None and found.id == attachment.id

    async def test_returns_none_for_an_unknown_storage_key(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyVisitAttachmentRepository(db_session)
        assert await repo.get_by_storage_key("does/not/exist.png") is None


class TestGetByChecksum:
    async def test_returns_the_matching_attachment(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitAttachmentRepository(db_session)
        checksum = Sha256Checksum(_unique_checksum())

        attachment = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="scan.png",
            original_file_name="scan.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=f"visits/{visit.id}/scan.png",
            checksum_sha256=checksum,
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(attachment)
        await db_session.commit()

        found = await repo.get_by_checksum(checksum)
        assert found is not None and found.id == attachment.id

    async def test_returns_none_for_an_unknown_checksum(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyVisitAttachmentRepository(db_session)
        assert await repo.get_by_checksum(Sha256Checksum(_unique_checksum())) is None


class TestListByVisit:
    async def test_returns_attachments_ordered_by_uploaded_at_scoped_to_the_visit(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyVisitAttachmentRepository(db_session)

        await repo.add(
            VisitAttachment.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                attachment_type=AttachmentType.IMAGE,
                file_name="second.png",
                original_file_name="second.png",
                mime_type="image/png",
                file_size_bytes=1024,
                storage_provider=StorageProvider.S3,
                storage_bucket="drassist-attachments",
                storage_key=f"visits/{visit_a.id}/second.png",
                checksum_sha256=Sha256Checksum(_unique_checksum()),
                uploaded_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            VisitAttachment.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                attachment_type=AttachmentType.IMAGE,
                file_name="first.png",
                original_file_name="first.png",
                mime_type="image/png",
                file_size_bytes=1024,
                storage_provider=StorageProvider.S3,
                storage_bucket="drassist-attachments",
                storage_key=f"visits/{visit_a.id}/first.png",
                checksum_sha256=Sha256Checksum(_unique_checksum()),
                uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            VisitAttachment.create(
                organization_id=organization.id,
                visit_id=visit_b.id,
                attachment_type=AttachmentType.IMAGE,
                file_name="unrelated.png",
                original_file_name="unrelated.png",
                mime_type="image/png",
                file_size_bytes=1024,
                storage_provider=StorageProvider.S3,
                storage_bucket="drassist-attachments",
                storage_key=f"visits/{visit_b.id}/unrelated.png",
                checksum_sha256=Sha256Checksum(_unique_checksum()),
                uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await db_session.commit()

        attachments = await repo.list_by_visit(visit_a.id)
        assert [a.file_name for a in attachments] == ["first.png", "second.png"]


class TestStorageKeyUniqueness:
    async def test_duplicate_storage_key_across_different_visits_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyVisitAttachmentRepository(db_session)
        shared_storage_key = "visits/shared-key/scan.png"

        first = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit_a.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="scan.png",
            original_file_name="scan.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=shared_storage_key,
            checksum_sha256=Sha256Checksum(_unique_checksum()),
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(first)
        await db_session.commit()

        second = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit_b.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="scan.png",
            original_file_name="scan.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=shared_storage_key,
            checksum_sha256=Sha256Checksum(_unique_checksum()),
            uploaded_at=datetime(2026, 1, 1, 9, 5, tzinfo=UTC),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestChecksumUniqueness:
    async def test_duplicate_checksum_across_different_visits_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyVisitAttachmentRepository(db_session)
        shared_checksum = Sha256Checksum(_unique_checksum())

        first = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit_a.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="scan-a.png",
            original_file_name="scan-a.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=f"visits/{visit_a.id}/scan-a.png",
            checksum_sha256=shared_checksum,
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(first)
        await db_session.commit()

        second = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit_b.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="scan-b.png",
            original_file_name="scan-b.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=f"visits/{visit_b.id}/scan-b.png",
            checksum_sha256=shared_checksum,
            uploaded_at=datetime(2026, 1, 1, 9, 5, tzinfo=UTC),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestVisitAttachmentRequiresValidReferences:
    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyVisitAttachmentRepository(db_session)

        attachment = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=uuid4(),
            attachment_type=AttachmentType.IMAGE,
            file_name="orphaned.png",
            original_file_name="orphaned.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=f"visits/{uuid4()}/orphaned.png",
            checksum_sha256=Sha256Checksum(_unique_checksum()),
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(attachment)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_uploaded_by_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitAttachmentRepository(db_session)

        attachment = VisitAttachment.create(
            organization_id=organization.id,
            visit_id=visit.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="orphaned-attribution.png",
            original_file_name="orphaned-attribution.png",
            mime_type="image/png",
            file_size_bytes=1024,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=f"visits/{visit.id}/orphaned-attribution.png",
            checksum_sha256=Sha256Checksum(_unique_checksum()),
            uploaded_by=uuid4(),
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(attachment)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestFileSizeCheckConstraint:
    """`VisitAttachment.__post_init__` already prevents this state from
    ever existing via the domain layer — this test targets the DB
    `CHECK` constraint directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.procedures.test_visit_procedure_repository.TestCheckConstraints`
    already established."""

    async def test_non_positive_file_size_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitAttachmentModel(
            organization_id=organization.id,
            visit_id=visit.id,
            attachment_type=AttachmentType.IMAGE,
            file_name="bad-size.png",
            original_file_name="bad-size.png",
            mime_type="image/png",
            file_size_bytes=0,
            storage_provider=StorageProvider.S3,
            storage_bucket="drassist-attachments",
            storage_key=f"visits/{visit.id}/bad-size.png",
            checksum_sha256=_unique_checksum(),
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
