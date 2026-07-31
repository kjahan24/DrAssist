"""Enums owned by the Documents module's domain.

`StorageProvider` names *where* a document's bytes physically live — only
`LOCAL` has a concrete adapter in this task (`app.infrastructure.storage
.local_storage_provider.LocalStorageProvider`); `S3`/`AZURE_BLOB`/
`GOOGLE_CLOUD_STORAGE` are recorded here so `MedicalDocument.storage_provider`
can express them once a real adapter exists for each, without a schema
change — see `docs/backend-architecture` module-communication notes and
this module's own `container.py` scope note.
"""

from enum import StrEnum


class DocumentCategory(StrEnum):
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    RADIOLOGY = "radiology"
    MEDICAL_IMAGE = "medical_image"
    CLINICAL_NOTE = "clinical_note"
    REFERRAL_LETTER = "referral_letter"
    DISCHARGE_SUMMARY = "discharge_summary"
    INSURANCE = "insurance"
    CONSENT_FORM = "consent_form"
    VACCINATION = "vaccination"
    OTHER = "other"


class StorageProvider(StrEnum):
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD_STORAGE = "google_cloud_storage"


class DocumentStatus(StrEnum):
    UPLOADING = "uploading"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
