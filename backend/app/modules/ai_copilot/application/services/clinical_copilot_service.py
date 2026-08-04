"""`ClinicalCopilotService` — the orchestrator this task calls for.

Runs the 8-stage AI Request Pipeline this task specifies:

    Validation -> Context Assembly -> Prompt Rendering -> Provider
    Selection -> LLM Call -> Structured Parsing -> Validation -> Audit
    Logging -> Return DTO

1. **Validation** — `AIRequest` already validated itself in
   `domain/value_objects.py::AIRequest.__post_init__` (Tier 3-style: an
   invalid request cannot exist in memory), so there is nothing left to
   check here.
2. **Context Assembly** — `ContextBuilder.build`.
3. **Prompt Rendering** — `PromptBuilder.build_variables` +
   `.build_messages`.
4. **Provider Selection** — collapses to "use the injected
   `AIGatewayPort`" given AI Foundation's current public contract: that
   module exposes exactly one gateway (built once from
   `AISettings.default_provider`, per its own `container.py`), not a
   per-call provider choice — this module has no ability to select a
   *different* provider without AI Foundation exposing that on
   `AIGatewayPort`, which it doesn't today and which this task's "never
   modify completed modules" rule forbids adding. What this module *can*
   select is the `AIModel` (provider + model name) attached to the
   request: `model_override` on `AIRequest` swaps the model name while
   keeping AI Foundation's configured default provider, resolved via
   `infrastructure/provider_selection.py`.
5. **LLM Call** — `AIGatewayPort.generate_chat_completion` (rule 4: no
   direct provider SDK calls).
6. **Structured Parsing** — `CopilotOutputParserPort.parse`.
7. **Validation** — `AIResponseValidatorPort.validate`.
8. **Audit Logging** — `CopilotAuditLoggerPort.log_session` on success,
   `.log_failure` for the failure modes this module can itself detect and
   name (context assembly, parsing, response validation — see
   `domain/exceptions.py`'s module docstring for why AI-Foundation-
   originated failures are not caught/logged here).
9. **Return DTO** — `AIResponse`.
"""

from time import perf_counter
from uuid import UUID, uuid4

from app.modules.ai.public.dto import AIModel, ChatCompletionRequest
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.ai_copilot.application.dto import AIResponse
from app.modules.ai_copilot.application.ports import (
    AIResponseValidatorPort,
    CopilotAuditLoggerPort,
    CopilotOutputParserPort,
    CostEstimatorPort,
)
from app.modules.ai_copilot.application.services.context_builder import ContextBuilder
from app.modules.ai_copilot.application.services.prompt_builder import PromptBuilder
from app.modules.ai_copilot.domain.exceptions import (
    AIResponseValidationError,
    PatientNotFoundError,
    StructuredResponseParsingError,
)
from app.modules.ai_copilot.domain.value_objects import AIRequest, AISession


class ClinicalCopilotService:
    def __init__(
        self,
        *,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        ai_gateway: AIGatewayPort,
        output_parser: CopilotOutputParserPort,
        response_validator: AIResponseValidatorPort,
        audit_logger: CopilotAuditLoggerPort,
        cost_estimator: CostEstimatorPort,
        default_model: AIModel,
    ) -> None:
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._ai_gateway = ai_gateway
        self._output_parser = output_parser
        self._response_validator = response_validator
        self._audit_logger = audit_logger
        self._cost_estimator = cost_estimator
        self._default_model = default_model

    async def execute(self, request: AIRequest) -> AIResponse:
        request_id = uuid4()
        start = perf_counter()

        try:
            context = await self._context_builder.build(
                request.patient_id, visit_id=request.visit_id
            )
        except PatientNotFoundError as exc:
            await self._log_failure(
                request, request_id=request_id, stage="context_assembly", exc=exc
            )
            raise

        variables = self._prompt_builder.build_variables(context, extra=dict(request.variables))
        messages = await self._prompt_builder.build_messages(
            request_type=request.request_type,
            prompt_version=request.prompt_version,
            variables=variables,
        )

        model = self._resolve_model(request.model_override)
        chat_request = ChatCompletionRequest(messages=tuple(messages), model=model)
        chat_response = await self._ai_gateway.generate_chat_completion(chat_request)

        try:
            parsed_content = self._output_parser.parse(
                chat_response.message.content, request.output_format
            )
        except StructuredResponseParsingError as exc:
            await self._log_failure(request, request_id=request_id, stage="parsing", exc=exc)
            raise

        try:
            self._response_validator.validate(
                parsed_content,
                output_format=request.output_format,
                raw_text=chat_response.message.content,
            )
        except AIResponseValidationError as exc:
            await self._log_failure(request, request_id=request_id, stage="validation", exc=exc)
            raise

        latency_ms = (perf_counter() - start) * 1000
        estimated_cost_usd = self._cost_estimator.estimate(
            provider=chat_response.provider.value,
            model=chat_response.model.name,
            prompt_tokens=chat_response.usage.prompt_tokens,
            completion_tokens=chat_response.usage.completion_tokens,
        )
        session = AISession(
            request_id=request_id,
            provider=chat_response.provider.value,
            model=chat_response.model.name,
            prompt_name=request.request_type,
            prompt_version=request.prompt_version,
            latency_ms=latency_ms,
            prompt_tokens=chat_response.usage.prompt_tokens,
            completion_tokens=chat_response.usage.completion_tokens,
            total_tokens=chat_response.usage.total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )
        await self._audit_logger.log_session(
            session, request_type=request.request_type, patient_id=request.patient_id
        )

        return AIResponse(
            output_format=request.output_format,
            raw_text=chat_response.message.content,
            parsed_content=parsed_content,
            session=session,
        )

    def _resolve_model(self, model_override: str | None) -> AIModel:
        if model_override is None:
            return self._default_model
        return AIModel(provider=self._default_model.provider, name=model_override)

    async def _log_failure(
        self, request: AIRequest, *, request_id: UUID, stage: str, exc: Exception
    ) -> None:
        await self._audit_logger.log_failure(
            request_id=request_id,
            request_type=request.request_type,
            patient_id=request.patient_id,
            stage=stage,
            error_code=type(exc).__name__,
            message=str(exc),
        )
