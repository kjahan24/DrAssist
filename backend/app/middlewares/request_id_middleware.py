"""Attaches a unique request ID to every inbound request.

The ID is bound into structlog's contextvars so every log line emitted
while handling the request automatically carries it, and is echoed back
via the `X-Request-ID` response header for client-side correlation.
"""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import RequestHeader


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(RequestHeader.REQUEST_ID, str(uuid.uuid4()))

        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")

        response.headers[RequestHeader.REQUEST_ID] = request_id
        return response
