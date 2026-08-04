"""`GenerateSOAPNoteUseCase` — orchestrates the pipeline this task
specifies:

    (input already validated by `SOAPEncounterInput.__post_init__`)
    -> `SOAPGeneratorPort.generate` (prompt selection, prompt rendering,
       provider selection, and the LLM call all happen inside this one
       port call — see `infrastructure/generation/soap_note_generator.py`)
    -> `SOAPNoteParserPort.parse` (raw AI text -> structured `SOAPNote`)
    -> `SOAPNoteValidatorPort.validate` (missing/empty/duplicated
       sections, hallucinated placeholders, invalid markdown)
    -> audit logging (success or failure)
    -> return `GeneratedSOAPNote`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation during `generator.generate()` propagate
unwrapped and unaudited-by-this-module, the same reasoning
`app.modules.clinical_note_ai.application.use_cases
.generate_clinical_note.GenerateClinicalNoteUseCase` documents for
itself.
"""

from app.modules.soap_note_ai.application.dto import GeneratedSOAPNote
from app.modules.soap_note_ai.application.ports import (
    SOAPGeneratorPort,
    SOAPNoteAuditLoggerPort,
    SOAPNoteParserPort,
    SOAPNoteValidatorPort,
)
from app.modules.soap_note_ai.domain.exceptions import (
    DuplicatedSOAPSectionError,
    EmptySOAPResponseError,
    HallucinatedPlaceholderError,
    InvalidMarkdownFormatError,
    InvalidSOAPNoteFormatError,
    MissingSOAPSectionError,
)
from app.modules.soap_note_ai.domain.value_objects import SOAPEncounterInput
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidSOAPNoteFormatError,
    MissingSOAPSectionError,
    EmptySOAPResponseError,
    DuplicatedSOAPSectionError,
    HallucinatedPlaceholderError,
    InvalidMarkdownFormatError,
)


class GenerateSOAPNoteUseCase(UseCase[SOAPEncounterInput, GeneratedSOAPNote]):
    def __init__(
        self,
        *,
        generator: SOAPGeneratorPort,
        parser: SOAPNoteParserPort,
        validator: SOAPNoteValidatorPort,
        audit_logger: SOAPNoteAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._audit_logger = audit_logger

    async def execute(self, input_dto: SOAPEncounterInput) -> GeneratedSOAPNote:
        raw_text, session = await self._generator.generate(input_dto)

        try:
            note = self._parser.parse(raw_text, output_format=input_dto.output_format)
            self._validator.validate(note)
        except _LOCAL_PIPELINE_ERRORS as exc:
            await self._audit_logger.log_failure(
                generation_id=session.generation_id,
                organization_id=input_dto.organization_id,
                patient_id=input_dto.patient_id,
                stage="parse_or_validate",
                error_code=type(exc).__name__,
                message=str(exc),
            )
            raise

        await self._audit_logger.log_generation(
            session, organization_id=input_dto.organization_id, patient_id=input_dto.patient_id
        )
        return GeneratedSOAPNote(note=note, session=session)
