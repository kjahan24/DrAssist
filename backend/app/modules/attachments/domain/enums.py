"""Enums owned by the Attachments module's domain."""

from enum import StrEnum


class AttachmentType(StrEnum):
    IMAGE = "image"
    PDF = "pdf"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class StorageProvider(StrEnum):
    LOCAL = "local"
    MINIO = "minio"
    S3 = "s3"
