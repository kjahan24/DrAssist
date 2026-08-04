"""FastAPI dependency providers for the AI module.

Empty for this task — no endpoints exist yet (`router.py`'s own
docstring). A future AI-feature module wanting a `Depends()`-injected
`AIGatewayFacade` can wrap `app.modules.ai.container.get_ai_gateway_facade`
here (or import it directly, since it takes no per-request arguments).
"""
