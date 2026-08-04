"""Pydantic request/response schemas for the AI Prescription Assistance
module's HTTP surface.

Empty for now — `presentation/router.py` exposes only a placeholder
health route (no request/response bodies yet), the same "structure-only,
placeholder-endpoints-only" scope
`app.modules.icd10_ai.presentation.schemas` establishes for its own
module. A future authenticated generation endpoint defines its request/
response schemas here, built from `public/dto.py`'s shapes.
"""
