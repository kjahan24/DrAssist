"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.value_objects import Sha256Checksum
from app.modules.attachments.infrastructure.models import VisitAttachmentModel


def visit_attachment_to_domain(model: VisitAttachmentModel) -> VisitAttachment:
    return VisitAttachment(
        id=model.id,
        organization_id=model.organization_id,
        visit_id=model.visit_id,
        attachment_type=model.attachment_type,
        file_name=model.file_name,
        original_file_name=model.original_file_name,
        mime_type=model.mime_type,
        file_size_bytes=model.file_size_bytes,
        storage_provider=model.storage_provider,
        storage_bucket=model.storage_bucket,
        storage_key=model.storage_key,
        checksum_sha256=Sha256Checksum(model.checksum_sha256),
        uploaded_by=model.uploaded_by,
        uploaded_at=model.uploaded_at,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_visit_attachment_to_model(entity: VisitAttachment, model: VisitAttachmentModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.visit_id = entity.visit_id
    model.attachment_type = entity.attachment_type
    model.file_name = entity.file_name
    model.original_file_name = entity.original_file_name
    model.mime_type = entity.mime_type
    model.file_size_bytes = entity.file_size_bytes
    model.storage_provider = entity.storage_provider
    model.storage_bucket = entity.storage_bucket
    model.storage_key = entity.storage_key
    model.checksum_sha256 = str(entity.checksum_sha256)
    model.uploaded_by = entity.uploaded_by
    model.uploaded_at = entity.uploaded_at
    model.description = entity.description
