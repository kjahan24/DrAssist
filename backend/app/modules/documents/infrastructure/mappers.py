"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

Bridges the domain's `DocumentStatus.DELETED` business status to the
infrastructure-only `deleted_at` soft-delete column (see
`domain/entities.py`'s module docstring for why the domain layer itself
never touches `deleted_at` directly).
"""

from datetime import UTC, datetime

from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentStatus
from app.modules.documents.domain.value_objects import Sha256Checksum
from app.modules.documents.infrastructure.models import MedicalDocumentModel


def medical_document_to_domain(model: MedicalDocumentModel) -> MedicalDocument:
    return MedicalDocument(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        uploaded_by_user_id=model.uploaded_by_user_id,
        visit_id=model.visit_id,
        appointment_id=model.appointment_id,
        category=model.category,
        title=model.title,
        original_filename=model.original_filename,
        stored_filename=model.stored_filename,
        mime_type=model.mime_type,
        extension=model.extension,
        file_size_bytes=model.file_size_bytes,
        storage_provider=model.storage_provider,
        storage_path=model.storage_path,
        checksum_sha256=Sha256Checksum(model.checksum_sha256),
        status=model.status,
        uploaded_at=model.uploaded_at,
        description=model.description,
        tags=model.tags,
        metadata=model.document_metadata,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_medical_document_to_model(entity: MedicalDocument, model: MedicalDocumentModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.uploaded_by_user_id = entity.uploaded_by_user_id
    model.visit_id = entity.visit_id
    model.appointment_id = entity.appointment_id
    model.category = entity.category
    model.title = entity.title
    model.original_filename = entity.original_filename
    model.stored_filename = entity.stored_filename
    model.mime_type = entity.mime_type
    model.extension = entity.extension
    model.file_size_bytes = entity.file_size_bytes
    model.storage_provider = entity.storage_provider
    model.storage_path = entity.storage_path
    model.checksum_sha256 = str(entity.checksum_sha256)
    model.status = entity.status
    model.uploaded_at = entity.uploaded_at
    model.description = entity.description
    model.tags = entity.tags
    model.document_metadata = entity.metadata
    model.deleted_at = datetime.now(UTC) if entity.status is DocumentStatus.DELETED else None
