"""`GenerateICD10SuggestionsUseCase` — orchestrates the pipeline this task
specifies:

    (input already validated by `ICD10CodingInput.__post_init__`)
    -> `ICD10GeneratorPort.generate` (prompt selection, prompt rendering,
       provider selection, and the LLM call all happen inside this one
       port call — see `infrastructure/generation/icd10_generator.py`)
    -> `ICD10SuggestionParserPort.parse` (raw AI text -> structured
       `ICD10SuggestionSet`)
    -> `ICD10SuggestionValidatorPort.validate` (empty/invalid/duplicate
       codes, hallucinated diagnoses, missing confidence scores)
    -> `ICD10RankingService.rank` (confidence, supporting evidence,
       clinical relevance — this task's own RANKING requirement, applied
       as the final pipeline step so callers receive an already-ordered
       result)
    -> audit logging (success or failure)
    -> return `GeneratedICD10Suggestions`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation during `generator.generate()` propagate
unwrapped and unaudited-by-this-module, the same reasoning
`app.modules.soap_note_ai.application.use_cases.generate_soap_note
.GenerateSOAPNoteUseCase` documents for itself. Ranking never raises (it
is a pure sort over already-validated data), so it sits outside the
try/except entirely.
"""

from app.modules.icd10_ai.application.dto import GeneratedICD10Suggestions
from app.modules.icd10_ai.application.ports import (
    ICD10AuditLoggerPort,
    ICD10GeneratorPort,
    ICD10SuggestionParserPort,
    ICD10SuggestionValidatorPort,
)
from app.modules.icd10_ai.application.services.icd10_ranking_service import ICD10RankingService
from app.modules.icd10_ai.domain.exceptions import (
    DuplicateICD10CodeError,
    EmptyICD10ResponseError,
    HallucinatedDiagnosisError,
    InvalidICD10CodeError,
    InvalidICD10ResponseFormatError,
    MissingConfidenceScoreError,
)
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidICD10ResponseFormatError,
    EmptyICD10ResponseError,
    InvalidICD10CodeError,
    DuplicateICD10CodeError,
    HallucinatedDiagnosisError,
    MissingConfidenceScoreError,
)


class GenerateICD10SuggestionsUseCase(UseCase[ICD10CodingInput, GeneratedICD10Suggestions]):
    def __init__(
        self,
        *,
        generator: ICD10GeneratorPort,
        parser: ICD10SuggestionParserPort,
        validator: ICD10SuggestionValidatorPort,
        ranking_service: ICD10RankingService,
        audit_logger: ICD10AuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._ranking_service = ranking_service
        self._audit_logger = audit_logger

    async def execute(self, input_dto: ICD10CodingInput) -> GeneratedICD10Suggestions:
        raw_text, session = await self._generator.generate(input_dto)

        try:
            suggestion_set = self._parser.parse(raw_text, output_format=input_dto.output_format)
            self._validator.validate(suggestion_set)
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

        ranked = self._ranking_service.rank(suggestion_set)

        await self._audit_logger.log_generation(
            session, organization_id=input_dto.organization_id, patient_id=input_dto.patient_id
        )
        return GeneratedICD10Suggestions(suggestions=ranked, session=session)
