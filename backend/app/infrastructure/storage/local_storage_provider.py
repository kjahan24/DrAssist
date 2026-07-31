"""Local-filesystem implementation of `StoragePort`.

The Documents module's (`app.modules.documents`) only concrete storage
adapter today — see that module's `domain/enums.py::StorageProvider` for
how `S3`/`AZURE_BLOB`/`GOOGLE_CLOUD_STORAGE` are reserved as future values
without a schema change, since every caller depends only on the shared
`StoragePort` ABC, never on this class directly.

Layout on disk: `{base_path}/{bucket}/{object_name}`. `bucket` is a
caller-supplied namespace (the Documents module passes a fixed constant —
see `app.modules.documents.application.constants` — mirroring how
`MinioSettings.bucket_name` is a single configured bucket rather than a
per-row database value); it is never read from settings here, so this
adapter stays reusable by any future module that also wants local-disk
storage.

File I/O is synchronous `pathlib` work executed via `asyncio.to_thread` so
it doesn't block the event loop; no `aiofiles` dependency is introduced
since this is the only caller today (see `requirements/base.txt`, which
does not carry it).
"""

import asyncio
import shutil
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from app.shared.application.storage_port import StoragePort


class InvalidObjectNameError(ValueError):
    """Raised when an object_name would escape its bucket directory (e.g.
    via an absolute path or `..` segments) — the only validation this
    adapter performs beyond what `StoragePort` itself requires."""

    def __init__(self, object_name: str) -> None:
        super().__init__(f"unsafe object_name: {object_name!r}")


class LocalStorageProvider(StoragePort):
    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)

    async def upload(
        self, *, bucket: str, object_name: str, data: BinaryIO, content_type: str
    ) -> str:
        del content_type  # local disk has no content-type metadata store
        path = self._resolve(bucket, object_name)
        await asyncio.to_thread(self._write_stream, path, data)
        return object_name

    async def download(self, *, bucket: str, object_name: str) -> bytes:
        path = self._resolve(bucket, object_name)
        if not await asyncio.to_thread(path.is_file):
            raise FileNotFoundError(f"no object found at {bucket}/{object_name}")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, *, bucket: str, object_name: str) -> None:
        path = self._resolve(bucket, object_name)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    async def get_presigned_url(
        self, *, bucket: str, object_name: str, expires_seconds: int = 3600
    ) -> str:
        raise NotImplementedError(
            "LocalStorageProvider has no public HTTP endpoint to sign a URL "
            "against; callers on local storage must download bytes via "
            "download() instead. Signed URLs become available once a real "
            "object-storage adapter (S3/Azure Blob/GCS) is implemented."
        )

    def _resolve(self, bucket: str, object_name: str) -> Path:
        object_path = PurePosixPath(object_name)
        if object_path.is_absolute() or ".." in object_path.parts:
            raise InvalidObjectNameError(object_name)
        return self._base_path / bucket / Path(*object_path.parts)

    @staticmethod
    def _write_stream(path: Path, data: BinaryIO) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            shutil.copyfileobj(data, f)
