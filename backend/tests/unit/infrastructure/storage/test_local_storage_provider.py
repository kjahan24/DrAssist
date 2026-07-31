"""Unit tests for `LocalStorageProvider` against a real temporary
filesystem directory (`tmp_path`) — no mocking, since this class's only
job is disk I/O."""

from io import BytesIO
from pathlib import Path

import pytest

from app.infrastructure.storage.local_storage_provider import (
    InvalidObjectNameError,
    LocalStorageProvider,
)


@pytest.fixture
def provider(tmp_path: Path) -> LocalStorageProvider:
    return LocalStorageProvider(str(tmp_path))


class TestUpload:
    async def test_writes_bytes_to_bucket_object_name_path_and_returns_object_name(
        self, provider: LocalStorageProvider, tmp_path: Path
    ) -> None:
        result = await provider.upload(
            bucket="medical-documents",
            object_name="abc123.pdf",
            data=BytesIO(b"hello world"),
            content_type="application/pdf",
        )

        assert result == "abc123.pdf"
        written = tmp_path / "medical-documents" / "abc123.pdf"
        assert written.read_bytes() == b"hello world"

    async def test_creates_intermediate_directories(
        self, provider: LocalStorageProvider, tmp_path: Path
    ) -> None:
        await provider.upload(
            bucket="new-bucket",
            object_name="nested/path/file.txt",
            data=BytesIO(b"content"),
            content_type="text/plain",
        )

        assert (tmp_path / "new-bucket" / "nested" / "path" / "file.txt").read_bytes() == (
            b"content"
        )

    @pytest.mark.parametrize("unsafe_name", ["../escape.txt", "/etc/passwd", "a/../../b.txt"])
    async def test_rejects_unsafe_object_names(
        self, provider: LocalStorageProvider, unsafe_name: str
    ) -> None:
        with pytest.raises(InvalidObjectNameError):
            await provider.upload(
                bucket="medical-documents",
                object_name=unsafe_name,
                data=BytesIO(b"malicious"),
                content_type="text/plain",
            )


class TestDownload:
    async def test_returns_previously_uploaded_bytes(self, provider: LocalStorageProvider) -> None:
        await provider.upload(
            bucket="medical-documents",
            object_name="doc.pdf",
            data=BytesIO(b"payload"),
            content_type="application/pdf",
        )

        result = await provider.download(bucket="medical-documents", object_name="doc.pdf")

        assert result == b"payload"

    async def test_raises_file_not_found_for_a_missing_object(
        self, provider: LocalStorageProvider
    ) -> None:
        with pytest.raises(FileNotFoundError):
            await provider.download(bucket="medical-documents", object_name="missing.pdf")


class TestDelete:
    async def test_removes_a_previously_uploaded_object(
        self, provider: LocalStorageProvider, tmp_path: Path
    ) -> None:
        await provider.upload(
            bucket="medical-documents",
            object_name="doc.pdf",
            data=BytesIO(b"payload"),
            content_type="application/pdf",
        )

        await provider.delete(bucket="medical-documents", object_name="doc.pdf")

        assert not (tmp_path / "medical-documents" / "doc.pdf").exists()

    async def test_deleting_a_missing_object_does_not_raise(
        self, provider: LocalStorageProvider
    ) -> None:
        await provider.delete(bucket="medical-documents", object_name="missing.pdf")


class TestGetPresignedUrl:
    async def test_raises_not_implemented(self, provider: LocalStorageProvider) -> None:
        with pytest.raises(NotImplementedError):
            await provider.get_presigned_url(bucket="medical-documents", object_name="doc.pdf")
