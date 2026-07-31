"""`DownloadMedicalDocument` — fetches the metadata row, then the actual
bytes from whichever `StoragePort` adapter is configured. Available for
any non-deleted document (`Active` or `Archived`); `get_by_id` already
excludes soft-deleted rows, so no extra status check is needed here.
"""

from app.modules.documents.application.constants import DOCUMENT_STORAGE_BUCKET
from app.modules.documents.application.dto import (
    DownloadMedicalDocumentInput,
    DownloadMedicalDocumentOutput,
)
from app.modules.documents.domain.exceptions import MedicalDocumentNotFoundError
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.shared.application.storage_port import StoragePort
from app.shared.application.use_case import UseCase


class DownloadMedicalDocument(UseCase[DownloadMedicalDocumentInput, DownloadMedicalDocumentOutput]):
    def __init__(
        self, *, document_repository: MedicalDocumentRepository, storage: StoragePort
    ) -> None:
        self._documents = document_repository
        self._storage = storage

    async def execute(
        self, input_dto: DownloadMedicalDocumentInput
    ) -> DownloadMedicalDocumentOutput:
        document = await self._documents.get_by_id(input_dto.document_id)
        if document is None:
            raise MedicalDocumentNotFoundError(input_dto.document_id)

        file_data = await self._storage.download(
            bucket=DOCUMENT_STORAGE_BUCKET, object_name=document.storage_path
        )

        return DownloadMedicalDocumentOutput(
            document_id=document.id,
            original_filename=document.original_filename,
            mime_type=document.mime_type,
            file_data=file_data,
        )
