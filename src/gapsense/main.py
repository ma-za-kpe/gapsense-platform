"""
GapSense Platform FastAPI Application

AI-powered foundational learning diagnostic platform for Ghana.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from gapsense.ai import get_prompt_library
from gapsense.config import settings
from gapsense.core.database import close_db, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events.

    Startup:
    - Load prompt library into memory
    - Verify database connection
    - Initialize services

    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # Startup
    print("🚀 GapSense Platform starting...")

    # Load prompt library
    prompt_lib = get_prompt_library()
    print(f"📚 Loaded {len(prompt_lib)} prompts (v{prompt_lib.metadata['version']})")

    # Verify database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

    print("✅ GapSense Platform ready!")

    yield

    # Shutdown
    print("🛑 GapSense Platform shutting down...")
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

    # Health check endpoints
    @app.get("/", tags=["Health"])
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "service": "GapSense Platform",
            "status": "operational",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/health", tags=["Health"], response_model=None)
    async def health_check() -> JSONResponse:
        """Health check endpoint for load balancers.

        Returns:
            - status: healthy/unhealthy
            - checks: Individual health checks
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
    from gapsense.api.v1 import curriculum, diagnostics, parents, teachers

    app.include_router(curriculum.router, prefix="/api/v1/curriculum", tags=["Curriculum"])
    app.include_router(diagnostics.router, prefix="/api/v1/diagnostics", tags=["Diagnostics"])
    app.include_router(parents.router, prefix="/api/v1/parents", tags=["Parents"])
    app.include_router(teachers.router, prefix="/api/v1/teachers", tags=["Teachers"])

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
