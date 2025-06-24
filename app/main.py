from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from app.core.config import get_settings
from app.core.exceptions import BillingException
from app.api.v1.router import api_router

settings = get_settings()

logger = structlog.get_logger()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Global Billing Service",
        description="Scalable billing and subscription management microservice",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
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

    # Exception handler
    @application.exception_handler(BillingException)
    async def billing_exception_handler(request: Request, exc: BillingException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.detail,
                    "status_code": exc.status_code,
                }
            },
        )

    # Include API routes
    application.include_router(api_router, prefix="/api/v1")

    # Health check
    @application.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": settings.APP_NAME}

    return application


app = create_app()
