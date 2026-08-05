"""`WorkflowExecutorService` — this task's own explicitly-named
APPLICATION service, the thin orchestration layer over
`WorkflowExecutorPort` that runs one step, covering every ERROR
HANDLING behavior this task's own section names:

- **Support skipping modules / graceful degradation** — before ever
  calling a step's own adapter, this service asks the adapter's own
  `check_prerequisites` for missing-prerequisite reasons and asks
  `WorkflowValidationService.validate_module_outputs` whether every
  declared dependency actually completed; either one raising
  (`MissingPrerequisiteError`/`MissingModuleOutputError`) is *caught
  here* and converted into a `WorkflowStepStatus.SKIPPED` result with a
  human-readable `skipped_reason` — never a fatal error. This is the
  deliberate default: a workflow with twelve orchestrated modules will
  routinely have some that simply have nothing to work with (no
  radiology findings were given, so `RADIOLOGY_INTERPRETATION` is
  skipped, not force-run against fabricated data) or whose own upstream
  dependency itself got skipped/failed — both are ordinary, expected
  outcomes, not bugs.
- **Support cancellation** — checked once at the very start of each
  step (never mid-step; this module makes no direct LLM call it could
  interrupt partway through — see `application/dto.py
  ::WorkflowCancellationToken`'s own docstring).
- **Support timeout** — `step.timeout_seconds`, when given, wraps the
  adapter's own `execute` call in `asyncio.wait_for`.
- **Support retry** — `step.max_retries` (default `0`) controls how many
  additional attempts follow an exception from the adapter's own
  `execute` call, immediately (no backoff — this task's own ERROR
  HANDLING section names "Retry strategy" without specifying one, and an
  immediate-retry loop is the simplest strategy that is not itself
  unrequested complexity).
- **Module failure isolation / partial success** — any exception the
  adapter's own `execute` raises (after retries are exhausted) is caught
  as broadly as this module is able to (`except Exception`): this module
  cannot import any of the twelve orchestrated peer modules' own
  `.domain` from outside those modules (module-independence rule), so it
  has no narrower, importable exception type to catch specifically — see
  `domain/exceptions.py`'s own module docstring for the same reasoning.
  A caught failure becomes a `WorkflowStepStatus.FAILED` result; it
  never propagates out of this method and never stops sibling steps
  from running.
"""

import asyncio
from collections.abc import Mapping
from dataclasses import replace
from time import perf_counter

from app.modules.ai_orchestrator.application.dto import WorkflowCancellationToken
from app.modules.ai_orchestrator.application.ports import WorkflowExecutorPort
from app.modules.ai_orchestrator.application.services.workflow_validation_service import (
    WorkflowValidationService,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.exceptions import (
    MissingModuleOutputError,
    MissingPrerequisiteError,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput,
    WorkflowStepDefinition,
    WorkflowStepResult,
)


class WorkflowExecutorService:
    def __init__(
        self,
        *,
        adapters: Mapping[WorkflowModule, WorkflowExecutorPort],
        validation_service: WorkflowValidationService,
    ) -> None:
        self._adapters = adapters
        self._validation_service = validation_service

    async def execute_step(
        self,
        step: WorkflowStepDefinition,
        bundle: WorkflowExecutionInput,
        context: Mapping[WorkflowModule, str],
        completed_results: Mapping[WorkflowModule, WorkflowStepResult],
        *,
        cancellation_token: WorkflowCancellationToken | None = None,
    ) -> WorkflowStepResult:
        if cancellation_token is not None and cancellation_token.is_cancelled:
            return WorkflowStepResult(
                module=step.module,
                status=WorkflowStepStatus.CANCELLED,
                skipped_reason="workflow was cancelled before this step started",
            )

        adapter = self._adapters[step.module]

        try:
            self._validation_service.validate_prerequisites(
                step, adapter.check_prerequisites(bundle)
            )
            self._validation_service.validate_module_outputs(step, completed_results)
        except (MissingPrerequisiteError, MissingModuleOutputError) as exc:
            return WorkflowStepResult(
                module=step.module,
                status=WorkflowStepStatus.SKIPPED,
                skipped_reason=str(exc),
            )

        return await self._run_with_retries(step, adapter, bundle, context)

    async def _run_with_retries(
        self,
        step: WorkflowStepDefinition,
        adapter: WorkflowExecutorPort,
        bundle: WorkflowExecutionInput,
        context: Mapping[WorkflowModule, str],
    ) -> WorkflowStepResult:
        attempt = 0
        last_error: Exception | None = None
        start = perf_counter()

        while attempt <= step.max_retries:
            attempt += 1
            try:
                if step.timeout_seconds is not None:
                    result = await asyncio.wait_for(
                        adapter.execute(bundle, context), timeout=step.timeout_seconds
                    )
                else:
                    result = await adapter.execute(bundle, context)
                return replace(result, attempt_count=attempt)
            except TimeoutError:
                last_error = TimeoutError(f"step timed out after {step.timeout_seconds}s")
            except Exception as exc:  # deliberately broad — see module docstring
                last_error = exc

        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=step.module,
            status=WorkflowStepStatus.FAILED,
            latency_ms=latency_ms,
            attempt_count=attempt,
            error_message=str(last_error) if last_error is not None else "unknown error",
        )
