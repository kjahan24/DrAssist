"""Port for object storage (implemented by MinIO in `app/infrastructure/storage/`)."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StoragePort(ABC):
    @abstractmethod
    async def upload(
        self, *, bucket: str, object_name: str, data: BinaryIO, content_type: str
    ) -> str: ...

    @abstractmethod
    async def download(self, *, bucket: str, object_name: str) -> bytes: ...

    @abstractmethod
    async def delete(self, *, bucket: str, object_name: str) -> None: ...

    @abstractmethod
    async def get_presigned_url(
        self, *, bucket: str, object_name: str, expires_seconds: int = 3600
    ) -> str: ...
