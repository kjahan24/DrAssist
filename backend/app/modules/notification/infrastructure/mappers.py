"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`model.notification_metadata` <-> `entity.metadata` is the one field
whose name differs between the two shapes — see
`infrastructure/models.py` for why (`Base.metadata`'s name collision).
"""

from app.modules.notification.domain.entities import Notification
from app.modules.notification.infrastructure.models import NotificationModel


def notification_to_domain(model: NotificationModel) -> Notification:
    return Notification(
        id=model.id,
        organization_id=model.organization_id,
        recipient_user_id=model.recipient_user_id,
        notification_type=model.notification_type,
        title=model.title,
        message=model.message,
        priority=model.priority,
        status=model.status,
        reference_type=model.reference_type,
        reference_id=model.reference_id,
        scheduled_at=model.scheduled_at,
        sent_at=model.sent_at,
        read_at=model.read_at,
        expires_at=model.expires_at,
        metadata=model.notification_metadata,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_notification_to_model(entity: Notification, model: NotificationModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.recipient_user_id = entity.recipient_user_id
    model.notification_type = entity.notification_type
    model.title = entity.title
    model.message = entity.message
    model.priority = entity.priority
    model.status = entity.status
    model.reference_type = entity.reference_type
    model.reference_id = entity.reference_id
    model.scheduled_at = entity.scheduled_at
    model.sent_at = entity.sent_at
    model.read_at = entity.read_at
    model.expires_at = entity.expires_at
    model.notification_metadata = entity.metadata
