"""`DeleteMedicalDocument` (Archived -> Deleted).

Soft-delete only: the ORM mapper marks `deleted_at` (see
`infrastructure/mappers.py`), but the underlying file is left in place on
the configured `StoragePort` adapter. This task explicitly excludes
background jobs, and this task's own business rules say "deleted
documents are soft deleted" — not "physically erased" — so an eventual,
policy-driven physical purge (retention/compliance-scheduled) is left for
a future task rather than being triggered synchronously here.
"""

from app.modules.documents.application.dto import (
    DeleteMedicalDocumentInput,
    MedicalDocumentStatusOutput,
)
from app.modules.documents.domain.exceptions import MedicalDocumentNotFoundError
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class DeleteMedicalDocument(UseCase[DeleteMedicalDocumentInput, MedicalDocumentStatusOutput]):
    def __init__(
        self, *, document_repository: MedicalDocumentRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._documents = document_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: DeleteMedicalDocumentInput) -> MedicalDocumentStatusOutput:
        document = await self._documents.get_by_id(input_dto.document_id)
        if document is None:
            raise MedicalDocumentNotFoundError(input_dto.document_id)

        document.soft_delete()
        await self._documents.add(document)
        self._uow.collect_events(document.pull_events())
        await self._uow.commit()

        return MedicalDocumentStatusOutput(document_id=document.id, status=document.status)
