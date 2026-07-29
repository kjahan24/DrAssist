"""Domain exceptions for the Attachments module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. A
missing referenced `Visit`/`Doctor` raises the *owning* module's own
`PatientVisitNotFoundError`/`DoctorNotFoundError` directly (see
`application/use_cases/upload_attachment.py`), not an Attachments-specific
wrapper — the same cross-module reuse already established by
`app.modules.procedures.application.use_cases.record_procedure.RecordVisitProcedure`.
"""

from app.shared.domain.exceptions import DomainError


class FileNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("file_name must not be blank")


class OriginalFileNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("original_file_name must not be blank")


class MimeTypeRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("mime_type must not be blank")


class StorageBucketRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("storage_bucket must not be blank")


class StorageKeyRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("storage_key must not be blank")


class NonPositiveFileSizeError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"file_size_bytes must be greater than zero, got {value}")
        self.value = value


class InvalidSha256ChecksumError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value!r} is not a valid SHA-256 checksum")
        self.value = value


class DuplicateStorageKeyError(DomainError):
    def __init__(self, storage_key: str) -> None:
        super().__init__(f"storage_key {storage_key!r} is already in use")
        self.storage_key = storage_key


class DuplicateChecksumError(DomainError):
    def __init__(self, checksum_sha256: str) -> None:
        super().__init__(f"checksum_sha256 {checksum_sha256!r} is already in use")
        self.checksum_sha256 = checksum_sha256
