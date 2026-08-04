"""Pydantic request/response schemas for the AI Medical Reasoning
Engine's HTTP surface.

Empty for now — `presentation/router.py` exposes only a placeholder
health route (no request/response bodies yet), the same "structure-only,
placeholder-endpoints-only" scope
`app.modules.differential_diagnosis_ai.presentation.schemas` establishes
for its own module. This module is a reasoning layer consumed by other
backend modules through `public/interfaces.py::MedicalReasoningAIPort`,
not a clinician-facing HTTP API — see `presentation/router.py`'s own
docstring — so no authenticated generation endpoint is expected here.
"""
