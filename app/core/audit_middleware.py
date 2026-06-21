import time
import uuid
import json
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from app.database import async_session
from app.services.audit_service import AuditService
from app.config import settings

logger = logging.getLogger(__name__)

SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


def _should_skip(path: str, method: str) -> bool:
    if path in SKIP_PATHS or path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/redoc"):
        return True
    if method == "OPTIONS":
        return True
    return False


def _safe_truncate(data: Optional[str], max_len: int) -> Optional[str]:
    if data is None:
        return None
    if len(data) <= max_len:
        return data
    return data[:max_len] + "...[truncated]"


async def _read_body(request: Request) -> bytes:
    if not request.body:
        return b""
    chunks = []
    async for chunk in request.stream():
        chunks.append(chunk)
    return b"".join(chunks)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if _should_skip(request.url.path, request.method):
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:24]
        start_time = time.time()

        raw_body = await _read_body(request)

        async def receive():
            return {"type": "http.request", "body": raw_body, "more_body": False}

        request = Request(request.scope, receive)

        error_msg: Optional[str] = None
        status_code = 500
        response_body_text: Optional[str] = None

        try:
            response = await call_next(request)
            status_code = response.status_code

            if isinstance(response, StreamingResponse):
                body_chunks = [chunk async for chunk in response.body_iterator]
                response_body_bytes = b"".join(body_chunks)
                response = Response(
                    content=response_body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
                if response_body_bytes and len(response_body_bytes) < settings.AUDIT_BODY_MAX_SIZE:
                    try:
                        response_body_text = response_body_bytes.decode("utf-8", errors="replace")
                    except Exception:
                        response_body_text = None
            else:
                body = getattr(response, "body", b"")
                if body and len(body) < settings.AUDIT_BODY_MAX_SIZE:
                    try:
                        response_body_text = body.decode("utf-8", errors="replace")
                    except Exception:
                        response_body_text = None

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.exception("AuditMiddleware caught unhandled error")
            response = Response(
                content=json.dumps({"detail": "Internal Server Error"}),
                status_code=500,
                media_type="application/json",
            )
            raise
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            auth_ctx = getattr(request.state, "auth_context", None)

            request_body_text: Optional[str] = None
            if raw_body and len(raw_body) < settings.AUDIT_BODY_MAX_SIZE:
                try:
                    request_body_text = raw_body.decode("utf-8", errors="replace")
                except Exception:
                    request_body_text = None
            elif raw_body:
                request_body_text = f"[body too large: {len(raw_body)} bytes]"

            query_string = request.url.query
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            route = None
            for route_obj in request.app.routes:
                match, _ = route_obj.matches(request.scope)
                if match:
                    route = route_obj.path
                    break

            try:
                async with async_session() as db:
                    svc = AuditService(db)
                    await svc.create_log(
                        request_id=request_id,
                        app_id=auth_ctx.app_id if auth_ctx else None,
                        api_key=auth_ctx.api_key if auth_ctx else None,
                        method=request.method,
                        path=request.url.path,
                        route=route,
                        query_params=_safe_truncate(query_string, 1024) if query_string else None,
                        request_body=_safe_truncate(request_body_text, settings.AUDIT_BODY_MAX_SIZE),
                        status_code=status_code,
                        response_body=_safe_truncate(response_body_text, settings.AUDIT_BODY_MAX_SIZE),
                        client_ip=client_ip,
                        user_agent=_safe_truncate(user_agent, 512),
                        latency_ms=latency_ms,
                        error_message=_safe_truncate(error_msg, 4096),
                    )
            except Exception as log_err:
                logger.error(f"Failed to write audit log: {log_err}")

        response.headers["X-Request-ID"] = request_id
        return response
