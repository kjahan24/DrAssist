"""Data Transfer Objects for the AI Risk Stratification & Early Warning
Score module's application layer — use-case input/output shapes that
aren't already a domain value object in their own right."""

from dataclasses import dataclass

from app.modules.risk_stratification_ai.domain.value_objects import (
    GenerationSession,
    RiskStratificationResult,
)


@dataclass(frozen=True, slots=True)
class GeneratedRiskStratification:
    """`AnalyzePatientRiskUseCase`'s output — bundles the enriched result
    with its `GenerationSession`, the same "result + session" shape
    every prior AI module's own use-case DTO establishes for itself."""

    result: RiskStratificationResult
    session: GenerationSession
