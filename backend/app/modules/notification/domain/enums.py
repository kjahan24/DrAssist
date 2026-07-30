from enum import StrEnum


class NotificationType(StrEnum):
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    VISIT_COMPLETED = "visit_completed"
    PRESCRIPTION_READY = "prescription_ready"
    LAB_RESULT_READY = "lab_result_ready"
    GENERAL = "general"
    SYSTEM = "system"


class NotificationPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
