"""`PrescriptionAIFacade` — the one concrete implementation of
`PrescriptionAIPort`. Constructed by `app.modules.prescription_ai
.container.get_prescription_ai_facade`.

`render_suggestions` delegates directly to `PrescriptionSuggestionRenderer`
(not a use case) — see that service's own module docstring for why: this
task names exactly three use cases, none of them a rendering one.
`analyze_medication_safety` delegates to `AnalyzeMedicationSafetyUseCase`
via a small `MedicationSafetyAnalysisInput` DTO, matching the shape that
use case's own `execute` expects.
"""

from collections.abc import AsyncIterator

from app.modules.prescription_ai.application.dto import MedicationSafetyAnalysisInput
from app.modules.prescription_ai.application.ports import PrescriptionGeneratorPort
from app.modules.prescription_ai.application.services.prescription_suggestion_renderer import (
    PrescriptionSuggestionRenderer,
)
from app.modules.prescription_ai.application.use_cases.analyze_medication_safety import (
    AnalyzeMedicationSafetyUseCase,
)
from app.modules.prescription_ai.application.use_cases.generate_prescription_suggestion import (
    GeneratePrescriptionSuggestionUseCase,
)
from app.modules.prescription_ai.application.use_cases.validate_prescription_context import (
    ValidatePrescriptionContextUseCase,
)
from app.modules.prescription_ai.public.dto import (
    GeneratedPrescriptionSuggestions,
    MedicationSafetyFinding,
    PrescriptionContextInput,
    PrescriptionContextValidationResultDTO,
    PrescriptionOutputFormat,
    PrescriptionStreamChunk,
    PrescriptionSuggestionSet,
)
from app.modules.prescription_ai.public.interfaces import PrescriptionAIPort


class PrescriptionAIFacade(PrescriptionAIPort):
    def __init__(
        self,
        *,
        generate_use_case: GeneratePrescriptionSuggestionUseCase,
        validate_use_case: ValidatePrescriptionContextUseCase,
        analyze_safety_use_case: AnalyzeMedicationSafetyUseCase,
        renderer: PrescriptionSuggestionRenderer,
        generator: PrescriptionGeneratorPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._validate_use_case = validate_use_case
        self._analyze_safety_use_case = analyze_safety_use_case
        self._renderer = renderer
        self._generator = generator

    async def generate_suggestion(
        self, context: PrescriptionContextInput
    ) -> GeneratedPrescriptionSuggestions:
        return await self._generate_use_case.execute(context)

    def stream_generate_suggestion(
        self, context: PrescriptionContextInput
    ) -> AsyncIterator[PrescriptionStreamChunk]:
        return self._generator.stream_generate(context)

    async def analyze_medication_safety(
        self,
        suggestion_set: PrescriptionSuggestionSet,
        *,
        existing_medications: tuple[str, ...] = (),
        allergies: tuple[str, ...] = (),
    ) -> tuple[MedicationSafetyFinding, ...]:
        return await self._analyze_safety_use_case.execute(
            MedicationSafetyAnalysisInput(
                medications=suggestion_set.medications,
                existing_medications=existing_medications,
                allergies=allergies,
            )
        )

    async def render_suggestions(
        self, suggestion_set: PrescriptionSuggestionSet, *, target_format: PrescriptionOutputFormat
    ) -> str:
        return self._renderer.render(suggestion_set, target_format)

    async def validate_context(
        self, context: PrescriptionContextInput
    ) -> PrescriptionContextValidationResultDTO:
        return await self._validate_use_case.execute(context)
