"""Integration tests for `SqlAlchemyMedicalDocumentRepository`, including
the FKs to `organizations`/`patients`/`users`/`patient_visits`/
`appointments`, the global `stored_filename` uniqueness constraint, and
the `file_size_bytes` `CHECK` constraint, against a real PostgreSQL
instance."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.documents._helpers import (
    persist_appointment,
    persist_full_chain,
    persist_organization,
    persist_patient,
    persist_user,
    persist_visit,
)

from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider
from app.modules.documents.domain.value_objects import Sha256Checksum
from app.modules.documents.infrastructure.models import MedicalDocumentModel
from app.modules.documents.infrastructure.repositories import SqlAlchemyMedicalDocumentRepository


def _unique_checksum() -> str:
    return (uuid4().hex + uuid4().hex)[:64]


def _make_document(
    *, organization_id: object, patient_id: object, uploaded_by_user_id: object, **overrides: object
) -> MedicalDocument:
    defaults: dict[str, object] = {
        "organization_id": organization_id,
        "patient_id": patient_id,
        "uploaded_by_user_id": uploaded_by_user_id,
        "category": DocumentCategory.LAB_REPORT,
        "title": "CBC Panel",
        "original_filename": "cbc-panel.pdf",
        "stored_filename": f"{uuid4().hex}.pdf",
        "mime_type": "application/pdf",
        "extension": ".pdf",
        "file_size_bytes": 20480,
        "storage_provider": StorageProvider.LOCAL,
        "storage_path": f"medical-documents/{uuid4().hex}.pdf",
        "checksum_sha256": Sha256Checksum(_unique_checksum()),
        "uploaded_at": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return MedicalDocument.create(**defaults)  # type: ignore[arg-type]


class TestMedicalDocumentRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, user, _doctor, visit, appointment = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyMedicalDocumentRepository(db_session)

        document = _make_document(
            organization_id=organization.id,
            patient_id=patient.id,
            uploaded_by_user_id=user.id,
            visit_id=visit.id,
            appointment_id=appointment.id,
            description="Complete blood count",
            tags=["urgent", "hematology"],
            metadata={"source": "lab-integration"},
        )
        document.activate()
        await repo.add(document)
        await db_session.commit()

        reloaded = await repo.get_by_id(document.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.patient_id == patient.id
        assert reloaded.uploaded_by_user_id == user.id
        assert reloaded.visit_id == visit.id
        assert reloaded.appointment_id == appointment.id
        assert reloaded.category is DocumentCategory.LAB_REPORT
        assert reloaded.title == "CBC Panel"
        assert reloaded.original_filename == "cbc-panel.pdf"
        assert reloaded.stored_filename == document.stored_filename
        assert reloaded.mime_type == "application/pdf"
        assert reloaded.extension == ".pdf"
        assert reloaded.file_size_bytes == 20480
        assert reloaded.storage_provider is StorageProvider.LOCAL
        assert reloaded.checksum_sha256 == document.checksum_sha256
        assert reloaded.status is DocumentStatus.ACTIVE
        assert reloaded.description == "Complete blood count"
        assert reloaded.tags == ["urgent", "hematology"]
        assert reloaded.metadata == {"source": "lab-integration"}

    async def test_optional_fields_round_trip_as_none(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        patient = await persist_patient(db_session, organization_id=organization.id)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyMedicalDocumentRepository(db_session)

        document = _make_document(
            organization_id=organization.id, patient_id=patient.id, uploaded_by_user_id=user.id
        )
        await repo.add(document)
        await db_session.commit()

        reloaded = await repo.get_by_id(document.id)
        assert reloaded is not None
        assert reloaded.visit_id is None
        assert reloaded.appointment_id is None
        assert reloaded.description is None
        assert reloaded.tags is None
        assert reloaded.metadata is None
        assert reloaded.status is DocumentStatus.UPLOADING


class TestGetByStoredFilename:
    async def test_returns_the_matching_document(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        patient = await persist_patient(db_session, organization_id=organization.id)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyMedicalDocumentRepository(db_session)
        stored_filename = f"{uuid4().hex}.pdf"

        document = _make_document(
            organization_id=organization.id,
            patient_id=patient.id,
            uploaded_by_user_id=user.id,
            stored_filename=stored_filename,
        )
        await repo.add(document)
        await db_session.commit()

        found = await repo.get_by_stored_filename(stored_filename)
        assert found is not None and found.id == document.id

    async def test_returns_none_for_an_unknown_stored_filename(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyMedicalDocumentRepository(db_session)
        assert await repo.get_by_stored_filename("does-not-exist.pdf") is None


class TestListByPatient:
    async def test_returns_documents_ordered_by_uploaded_at_descending_scoped_to_the_patient(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        patient_a = await persist_patient(db_session, organization_id=organization.id)
        patient_b = await persist_patient(db_session, organization_id=organization.id)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyMedicalDocumentRepository(db_session)

        await repo.add(
            _make_document(
                organization_id=organization.id,
                patient_id=patient_a.id,
                uploaded_by_user_id=user.id,
                title="first",
                uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            _make_document(
                organization_id=organization.id,
                patient_id=patient_a.id,
                uploaded_by_user_id=user.id,
                title="second",
                uploaded_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            _make_document(
                organization_id=organization.id,
                patient_id=patient_b.id,
                uploaded_by_user_id=user.id,
                title="unrelated",
                uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await db_session.commit()

        documents = await repo.list_by_patient(patient_a.id)
        assert [d.title for d in documents] == ["second", "first"]


class TestListByVisitAndAppointment:
    async def test_list_by_visit_and_list_by_appointment_scope_correctly(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, user, doctor, visit, appointment = await persist_full_chain(
            db_session
        )
        other_visit = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        other_appointment = await persist_appointment(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyMedicalDocumentRepository(db_session)

        await repo.add(
            _make_document(
                organization_id=organization.id,
                patient_id=patient.id,
                uploaded_by_user_id=user.id,
                visit_id=visit.id,
                appointment_id=appointment.id,
                title="matching",
            )
        )
        await repo.add(
            _make_document(
                organization_id=organization.id,
                patient_id=patient.id,
                uploaded_by_user_id=user.id,
                visit_id=other_visit.id,
                appointment_id=other_appointment.id,
                title="unrelated",
            )
        )
        await db_session.commit()

        by_visit = await repo.list_by_visit(visit.id)
        assert [d.title for d in by_visit] == ["matching"]

        by_appointment = await repo.list_by_appointment(appointment.id)
        assert [d.title for d in by_appointment] == ["matching"]


class TestStoredFilenameUniqueness:
    async def test_duplicate_stored_filename_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        patient = await persist_patient(db_session, organization_id=organization.id)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyMedicalDocumentRepository(db_session)
        shared_stored_filename = f"{uuid4().hex}.pdf"

        first = _make_document(
            organization_id=organization.id,
            patient_id=patient.id,
            uploaded_by_user_id=user.id,
            stored_filename=shared_stored_filename,
        )
        await repo.add(first)
        await db_session.commit()

        second = _make_document(
            organization_id=organization.id,
            patient_id=patient.id,
            uploaded_by_user_id=user.id,
            stored_filename=shared_stored_filename,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestChecksumIsNotUnique:
    """Unlike `visit_attachments.checksum_sha256`, this task's own rule
    states "same checksum may exist across different patients" — this
    test proves the schema actually allows it (no unique index)."""

    async def test_duplicate_checksum_across_different_patients_is_allowed(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        patient_a = await persist_patient(db_session, organization_id=organization.id)
        patient_b = await persist_patient(db_session, organization_id=organization.id)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyMedicalDocumentRepository(db_session)
        shared_checksum = Sha256Checksum(_unique_checksum())

        await repo.add(
            _make_document(
                organization_id=organization.id,
                patient_id=patient_a.id,
                uploaded_by_user_id=user.id,
                checksum_sha256=shared_checksum,
            )
        )
        await repo.add(
            _make_document(
                organization_id=organization.id,
                patient_id=patient_b.id,
                uploaded_by_user_id=user.id,
                checksum_sha256=shared_checksum,
            )
        )
        await db_session.commit()  # must not raise


class TestMedicalDocumentRequiresValidReferences:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyMedicalDocumentRepository(db_session)

        document = _make_document(
            organization_id=organization.id, patient_id=uuid4(), uploaded_by_user_id=user.id
        )
        await repo.add(document)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_uploaded_by_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyMedicalDocumentRepository(db_session)

        document = _make_document(
            organization_id=organization.id, patient_id=patient.id, uploaded_by_user_id=uuid4()
        )
        await repo.add(document)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestFileSizeCheckConstraint:
    """`MedicalDocument.__post_init__` already prevents this state from
    ever existing via the domain layer — this test targets the DB
    `CHECK` constraint directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.attachments.test_visit_attachment_repository.TestFileSizeCheckConstraint`
    already established."""

    async def test_non_positive_file_size_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        patient = await persist_patient(db_session, organization_id=organization.id)
        user = await persist_user(db_session, organization_id=organization.id)

        model = MedicalDocumentModel(
            organization_id=organization.id,
            patient_id=patient.id,
            uploaded_by_user_id=user.id,
            category=DocumentCategory.LAB_REPORT,
            title="Bad Size",
            original_filename="bad-size.pdf",
            stored_filename=f"{uuid4().hex}.pdf",
            mime_type="application/pdf",
            extension=".pdf",
            file_size_bytes=0,
            storage_provider=StorageProvider.LOCAL,
            storage_path=f"medical-documents/{uuid4().hex}.pdf",
            checksum_sha256=_unique_checksum(),
            status=DocumentStatus.UPLOADING,
            uploaded_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
