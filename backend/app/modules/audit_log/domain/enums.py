from enum import StrEnum


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"
    APPROVE = "approve"
    REJECT = "reject"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    VIEW = "view"


class AuditSource(StrEnum):
    API = "api"
    SYSTEM = "system"
    AI = "ai"
    BACKGROUND_JOB = "background_job"
