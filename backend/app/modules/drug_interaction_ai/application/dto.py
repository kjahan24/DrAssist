"""Data Transfer Objects for the AI Drug Interaction & Medication Safety
module's application layer — use-case input/output shapes that aren't
already a domain value object in their own right."""

from dataclasses import dataclass

from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisResult,
    GenerationSession,
)


@dataclass(frozen=True, slots=True)
class GeneratedDrugInteractionAnalysis:
    """`AnalyzeMedicationSafetyUseCase`'s output — bundles the enriched
    analysis result with its `GenerationSession`, the same "result +
    session" shape every prior AI module's own use-case DTO establishes
    for itself."""

    result: DrugInteractionAnalysisResult
    session: GenerationSession
