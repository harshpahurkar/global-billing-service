import logging
import time

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import BillingException

settings = get_settings()


def _configure_logging() -> None:
    """Configure structlog: JSON in production for CloudWatch parsing,
    human-readable console output in dev/test."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )


_configure_logging()
logger = structlog.get_logger()


def _error_response(status_code: int, message: str, **extra) -> JSONResponse:
    body = {"error": {"message": message, "status_code": status_code, **extra}}
    return JSONResponse(status_code=status_code, content=body)


def _rate_limit_key(request: Request) -> str:
    """Key rate limits by API key when one is present, otherwise by client IP.

    Authenticated callers each get their own bucket; anonymous bursts share the
    IP bucket. Webhook signatures are not API keys but we still want them
    bucketed by remote IP so a noisy peer doesn't starve everyone else.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    return get_remote_address(request)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Global Billing Service",
        description="Scalable billing and subscription management microservice",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Rate limiting. Disabled in testing so the suite can fire thousands of
    # requests per second from a single bucket without tripping the limit.
    if not settings.is_testing:
        limiter = Limiter(
            key_func=_rate_limit_key,
            default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
            headers_enabled=True,
        )
        application.state.limiter = limiter
        application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        application.add_middleware(SlowAPIMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        return response

    # Unified error envelope. BillingException is most-specific (a subclass of
    # HTTPException) and is matched first; raw HTTPException covers FastAPI's
    # own 401/404/405/etc.; RequestValidationError covers Pydantic 422s; a
    # generic handler catches anything else with a 500 envelope (and logs it).

    @application.exception_handler(BillingException)
    async def billing_exception_handler(request: Request, exc: BillingException):
        return _error_response(exc.status_code, exc.detail)

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return _error_response(exc.status_code, str(exc.detail))

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return _error_response(422, "Validation failed", details=exc.errors())

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled_exception", path=request.url.path)
        return _error_response(500, "Internal server error")

    application.include_router(api_router, prefix="/api/v1")

    @application.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": settings.APP_NAME}

    return application


app = create_app()
