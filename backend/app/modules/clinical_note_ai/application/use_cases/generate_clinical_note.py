"""`GenerateClinicalNoteUseCase` — orchestrates the pipeline this task
specifies:

    (input already validated by `ClinicalEncounterInput.__post_init__`)
    -> `ClinicalNoteGeneratorPort.generate` (prompt selection, prompt
       rendering, provider selection, and the LLM call all happen inside
       this one port call — see
       `infrastructure/generation/clinical_note_generator.py`)
    -> `ClinicalNoteParserPort.parse` (raw AI text -> structured
       `ClinicalNote`)
    -> `ClinicalNoteValidatorPort.validate` (missing sections, empty
       responses, hallucinated placeholders)
    -> audit logging (success or failure)
    -> return `GeneratedClinicalNote`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation during `generator.generate()` (timeouts,
rate limits, provider unavailability, ...) propagate unwrapped and
unaudited-by-this-module, the same "cannot import a peer module's
`.domain`, so cannot `isinstance`-check its exceptions" reasoning
`app.modules.ai_copilot.application.services.clinical_copilot_service`
documents for the identical situation.
"""

from app.modules.clinical_note_ai.application.dto import GeneratedClinicalNote
from app.modules.clinical_note_ai.application.ports import (
    ClinicalNoteAuditLoggerPort,
    ClinicalNoteGeneratorPort,
    ClinicalNoteParserPort,
    ClinicalNoteValidatorPort,
)
from app.modules.clinical_note_ai.domain.exceptions import (
    EmptyAIResponseError,
    HallucinatedPlaceholderError,
    InvalidClinicalNoteFormatError,
    MissingClinicalNoteSectionError,
)
from app.modules.clinical_note_ai.domain.value_objects import ClinicalEncounterInput
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidClinicalNoteFormatError,
    MissingClinicalNoteSectionError,
    EmptyAIResponseError,
    HallucinatedPlaceholderError,
)


class GenerateClinicalNoteUseCase(UseCase[ClinicalEncounterInput, GeneratedClinicalNote]):
    def __init__(
        self,
        *,
        generator: ClinicalNoteGeneratorPort,
        parser: ClinicalNoteParserPort,
        validator: ClinicalNoteValidatorPort,
        audit_logger: ClinicalNoteAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._audit_logger = audit_logger

    async def execute(self, input_dto: ClinicalEncounterInput) -> GeneratedClinicalNote:
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
        return GeneratedClinicalNote(note=note, session=session)
