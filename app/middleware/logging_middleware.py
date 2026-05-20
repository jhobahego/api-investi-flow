import logging
import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_id_var, user_id_var
from app.core.security import verify_token

logger = logging.getLogger("app.request")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures and stores request-specific context (X-Request-ID, User ID)
    and logs request initiation, completion, latency, and errors.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Retrieve or generate X-Request-ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Token tokens for request context variables
        token_request_id = request_id_var.set(request_id)
        token_user_id = None

        # Attempt to decode user ID (email) from Authorization header without throwing
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token_str = auth_header[7:]
            try:
                user_email = verify_token(token_str)
                if user_email:
                    token_user_id = user_id_var.set(user_email)
            except Exception:
                # Do not interrupt the pipeline; authentication validation dependencies
                # will handle actual auth errors on protected endpoints.
                pass

        start_time = time.perf_counter()
        logger.info(f"Iniciando request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000

            logger.info(
                f"Request completado: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Latencia: {process_time:.2f}ms"
            )

            # Propagate Request ID back to the client
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.exception(
                f"Request fallido: {request.method} {request.url.path} - "
                f"Error: {str(e)} - Latencia: {process_time:.2f}ms"
            )
            raise e
        finally:
            # Clean up contextvars context to prevent leaks (essential for persistent threads/tasks)
            request_id_var.reset(token_request_id)
            if token_user_id is not None:
                user_id_var.reset(token_user_id)
