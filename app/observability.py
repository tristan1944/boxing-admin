from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
from fastapi import HTTPException


class RequestTimingLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that measures request processing time and logs concise request/response info.

    Adds an 'X-Process-Time-Ms' header on responses to aid in quick diagnostics.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("request")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        client_ip = request.client.host if request.client else "?"
        path = request.url.path
        method = request.method
        status = response.status_code
        self.logger.info(
            "method=%s path=%s status=%s duration_ms=%s ip=%s",
            method,
            path,
            status,
            duration_ms,
            client_ip,
        )
        return response


def add_exception_handlers(app: FastAPI) -> None:
    """Register consistent error payload shapes for HTTP and generic exceptions."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        payload = {
            "ok": False,
            "error": {
                "status": exc.status_code,
                "message": exc.detail if isinstance(exc.detail, str) else "",
                "path": request.url.path,
            },
        }
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Do not leak internals; keep it simple.
        payload = {
            "ok": False,
            "error": {
                "status": 500,
                "message": "Internal server error",
                "path": request.url.path,
            },
        }
        logging.getLogger("error").exception("Unhandled exception: %s", exc)
        return JSONResponse(status_code=500, content=payload)


