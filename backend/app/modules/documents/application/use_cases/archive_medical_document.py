"""`ArchiveMedicalDocument` (Active -> Archived)."""

from app.modules.documents.application.dto import (
    ArchiveMedicalDocumentInput,
    MedicalDocumentStatusOutput,
)
from app.modules.documents.domain.exceptions import MedicalDocumentNotFoundError
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ArchiveMedicalDocument(UseCase[ArchiveMedicalDocumentInput, MedicalDocumentStatusOutput]):
    def __init__(
        self, *, document_repository: MedicalDocumentRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._documents = document_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: ArchiveMedicalDocumentInput) -> MedicalDocumentStatusOutput:
        document = await self._documents.get_by_id(input_dto.document_id)
        if document is None:
            raise MedicalDocumentNotFoundError(input_dto.document_id)

        document.archive()
        await self._documents.add(document)
        self._uow.collect_events(document.pull_events())
        await self._uow.commit()

        return MedicalDocumentStatusOutput(document_id=document.id, status=document.status)
