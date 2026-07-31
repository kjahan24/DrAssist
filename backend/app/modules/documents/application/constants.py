"""Cross-use-case constants for the Documents module.

`DOCUMENT_STORAGE_BUCKET` is the fixed storage namespace every
`StoragePort` call passes as `bucket` — `MedicalDocument` records only a
`storage_path` (the port's `object_name`), not a per-row bucket, so the
bucket itself is a single configured constant here rather than a database
value, mirroring how `MinioSettings.bucket_name` is one global setting
rather than a per-row value (see
`app.infrastructure.storage.local_storage_provider`'s own docstring).
"""

from typing import Final

DOCUMENT_STORAGE_BUCKET: Final = "medical-documents"
