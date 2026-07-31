"""`UpdateMedicalDocumentDetails` — only `title`/`description`/`tags`/
`category` are editable; see `MedicalDocument.update_details()`'s own
docstring for why every other field is immutable after upload.
"""

from app.modules.documents.application.dto import (
    UpdateMedicalDocumentDetailsInput,
    UpdateMedicalDocumentDetailsOutput,
)
from app.modules.documents.domain.exceptions import MedicalDocumentNotFoundError
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateMedicalDocumentDetails(
    UseCase[UpdateMedicalDocumentDetailsInput, UpdateMedicalDocumentDetailsOutput]
):
    def __init__(
        self, *, document_repository: MedicalDocumentRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._documents = document_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: UpdateMedicalDocumentDetailsInput
    ) -> UpdateMedicalDocumentDetailsOutput:
        document = await self._documents.get_by_id(input_dto.document_id)
        if document is None:
            raise MedicalDocumentNotFoundError(input_dto.document_id)

        document.update_details(
            title=input_dto.title,
            description=input_dto.description,
            tags=input_dto.tags,
            category=input_dto.category,
        )
        await self._documents.add(document)
        self._uow.collect_events(document.pull_events())
        await self._uow.commit()

        return UpdateMedicalDocumentDetailsOutput(document_id=document.id)
