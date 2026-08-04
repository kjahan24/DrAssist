"""Pydantic API schemas for the AI Clinical Note Generation module.

Empty for this task — `router.py` exposes a placeholder health route
only. A future consumer module (the real, persisted "Clinical Note"
feature) adds request/response schemas here, or in its own presentation
layer, following `app.schemas.base.ORJSONModel`, the same convention
every other module's own API schemas follow.
"""
