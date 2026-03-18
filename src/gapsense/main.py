"""
GapSense Platform FastAPI Application

AI-powered foundational learning diagnostic platform for Ghana.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from gapsense.ai import get_prompt_library
from gapsense.config import settings
from gapsense.core.database import close_db, engine

_logger = structlog.get_logger(__name__)

# Template setup
TEMPLATES_DIR = Path(__file__).parent / "web" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events.

    Startup:
    - Initialize AsyncAIClient singleton with connection pooling
    - Initialize PromptService and load v2.0 prompts
    - Initialize MediaService and verify S3 connectivity
    - Initialize GuardService
    - Verify database connectivity
    - Store services in app.state

    Shutdown:
    - Close AI client connection pool
    - Close database connections
    - Release all resources
    """
    import os

    # Startup
    print("🚀 GapSense Platform starting...")

    # 1. Verify database connection (critical — refuse to start on failure)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

    # 2. Load prompt library (critical — refuse to start on failure)
    prompt_lib = get_prompt_library()
    print(f"📚 Loaded {len(prompt_lib)} prompts (v{prompt_lib.metadata['version']})")

    # 3. Initialize PromptService with v2.0 multi-country support
    prompt_service = None
    try:
        from gapsense.ai.prompt_service import PromptService

        prompt_service = PromptService(settings)
        prompt_count = len(prompt_service.list_prompts())
        countries = prompt_service.get_supported_countries()
        print(f"📚 PromptService: {prompt_count} prompts, countries: {countries}")
    except Exception as e:
        print(f"❌ PromptService initialization failed: {e}")
        raise

    # 4. Initialize AsyncAIClient singleton
    ai_client = None
    try:
        from gapsense.ai.async_client import AsyncAIClient

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if anthropic_key:
            ai_client = AsyncAIClient(anthropic_api_key=anthropic_key)
            print("✅ AsyncAIClient initialized (Anthropic)")
        else:
            _logger.warning("ai_client_no_key", msg="ANTHROPIC_API_KEY not set")
            print("⚠️ AsyncAIClient: no API key, AI features disabled")
    except Exception as e:
        _logger.warning("ai_client_init_failed", error=str(e))
        print(f"⚠️ AsyncAIClient initialization failed: {e}")

    # 5. Initialize MediaService and verify S3 connectivity
    media_service = None
    s3_healthy = False
    try:
        from gapsense.services.media_service import MediaService

        media_service = MediaService(settings)
        s3_healthy = await media_service.verify_connectivity()
        if s3_healthy:
            print("✅ MediaService: S3 connectivity verified")
        else:
            print("⚠️ MediaService: S3 not reachable (degraded)")
    except Exception as e:
        _logger.warning("media_service_init_failed", error=str(e))
        print(f"⚠️ MediaService initialization failed: {e}")

    # 6. Initialize GuardService
    guard_service = None
    if ai_client and prompt_service:
        from gapsense.services.guard_service import GuardService

        guard_service = GuardService(ai_client, prompt_service)
        print("✅ GuardService initialized")

    # Store services in app.state for dependency injection
    app.state.ai_client = ai_client
    app.state.prompt_service = prompt_service
    app.state.media_service = media_service
    app.state.guard_service = guard_service
    app.state.s3_healthy = s3_healthy

    print("✅ GapSense Platform ready!")

    yield

    # Shutdown
    print("🛑 GapSense Platform shutting down...")
    if ai_client:
        await ai_client.close()
        print("✅ AI client connection pool closed")
    await close_db()
    print("✅ Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="GapSense Platform",
        description="AI-powered foundational learning diagnostic platform",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_local else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Landing page
    @app.get("/", response_class=HTMLResponse)
    async def landing_page(request: Request) -> HTMLResponse:
        """Root landing page."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/health", tags=["Health"], response_model=None)
    async def health_check() -> JSONResponse:
        """Health check endpoint for load balancers.

        Returns:
            - status: healthy/unhealthy
            - checks: Individual health checks (database, prompt_library, ai_client, s3)
        """
        checks: dict[str, dict[str, Any]] = {}

        # Database health
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = {"status": "healthy"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "error": str(e)}

        # Prompt library health
        try:
            prompt_lib = get_prompt_library()
            checks["prompt_library"] = {
                "status": "healthy",
                "prompts": len(prompt_lib),
                "version": prompt_lib.metadata["version"],
            }
        except Exception as e:
            checks["prompt_library"] = {"status": "unhealthy", "error": str(e)}

        # AI client readiness
        ai_client = getattr(app.state, "ai_client", None)
        if ai_client is not None:
            checks["ai_client"] = {"status": "healthy", "ready": True}
        else:
            checks["ai_client"] = {"status": "degraded", "ready": False}

        # S3 connectivity
        s3_healthy = getattr(app.state, "s3_healthy", False)
        media_service = getattr(app.state, "media_service", None)
        if media_service is not None:
            if s3_healthy:
                checks["s3"] = {"status": "healthy"}
            else:
                checks["s3"] = {"status": "unhealthy", "error": "S3 not reachable"}
        else:
            checks["s3"] = {"status": "degraded", "error": "MediaService not initialized"}

        # Overall status
        all_healthy = all(check["status"] == "healthy" for check in checks.values())
        status_code = 200 if all_healthy else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if all_healthy else "unhealthy",
                "environment": settings.ENVIRONMENT,
                "checks": checks,
            },
        )

    @app.get("/health/ready", tags=["Health"], response_model=None)
    async def readiness_check() -> dict[str, str] | JSONResponse:
        """Readiness check for Kubernetes.

        Returns 200 when app is ready to serve traffic.
        """
        # Check critical dependencies
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready"},
            )

    @app.get("/health/live", tags=["Health"])
    async def liveness_check() -> dict[str, str]:
        """Liveness check for Kubernetes.

        Returns 200 if app is alive (even if not fully functional).
        """
        return {"status": "alive"}

    # Register API routers
    from gapsense.api.v1 import curriculum, diagnostics, parents, schools, teachers
    from gapsense.web import demo
    from gapsense.webhooks import whatsapp

    app.include_router(curriculum.router, prefix="/api/v1/curriculum", tags=["Curriculum"])
    app.include_router(diagnostics.router, prefix="/api/v1/diagnostics", tags=["Diagnostics"])
    app.include_router(parents.router, prefix="/api/v1/parents", tags=["Parents"])
    app.include_router(schools.router, prefix="/api", tags=["Schools"])
    app.include_router(teachers.router, prefix="/api/v1/teachers", tags=["Teachers"])
    app.include_router(whatsapp.router, prefix="/v1")
    app.include_router(demo.router)  # Teacher demo UI

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "gapsense.main:app",
        host="0.0.0.0",  # nosec B104 - Intentional for containerized deployment
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
