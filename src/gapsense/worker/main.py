"""
GapSense Worker Service — Background Task Processor

SQS consumer for processing TTS generation, image analysis,
scheduled messages, and voice transcription tasks.
"""

import asyncio
import os
import signal
import sys

import structlog

logger = structlog.get_logger(__name__)


async def main() -> None:
    """Initialize services and start worker polling loop."""
    print("🚀 GapSense Worker starting...")

    # 1. Verify database connection (critical — refuse to start on failure)
    try:
        from sqlalchemy import text

        from gapsense.core.database import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

    # 2. Load settings
    from gapsense.config import settings

    print(f"📦 Environment: {settings.ENVIRONMENT}")

    # 3. Initialize PromptService
    try:
        from gapsense.ai.prompt_service import PromptService

        prompt_service = PromptService(settings)
        prompt_count = len(prompt_service.list_prompts())
        countries = prompt_service.get_supported_countries()
        print(f"📚 PromptService: {prompt_count} prompts, countries: {countries}")
    except Exception as e:
        print(f"❌ PromptService initialization failed: {e}")
        raise

    # 4. Initialize AsyncAIClient
    ai_client = None
    try:
        from gapsense.ai.async_client import AsyncAIClient

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if anthropic_key:
            ai_client = AsyncAIClient(anthropic_api_key=anthropic_key)
            print("✅ AsyncAIClient initialized (Anthropic)")
        else:
            logger.warning("ai_client_no_key", msg="ANTHROPIC_API_KEY not set")
            print("⚠️ AsyncAIClient: no API key, AI features disabled")
    except Exception as e:
        logger.warning("ai_client_init_failed", error=str(e))
        print(f"⚠️ AsyncAIClient initialization failed: {e}")

    # 5. Initialize MediaService
    try:
        from gapsense.services.media_service import MediaService

        media_service = MediaService(settings)
        s3_healthy = await media_service.verify_connectivity()
        if s3_healthy:
            print("✅ MediaService: S3 connectivity verified")
        else:
            print("⚠️ MediaService: S3 not reachable (degraded)")
    except Exception as e:
        logger.warning("media_service_init_failed", error=str(e))
        print(f"⚠️ MediaService initialization failed: {e}")
        raise

    # 6. Initialize GuardService
    guard_service = None
    if ai_client and prompt_service:
        from gapsense.services.guard_service import GuardService

        guard_service = GuardService(ai_client, prompt_service)
        print("✅ GuardService initialized")

    # 7. Initialize WorkerService (WITHOUT db session - each task gets its own)
    try:
        from gapsense.services.worker_service import WorkerService

        # WorkerService no longer takes a shared db session
        # Each task handler will create its own session as needed
        worker_service = WorkerService(
            ai_client=ai_client,
            media_service=media_service,
            guard_service=guard_service,
            prompt_service=prompt_service,
            settings=settings,
            db=None,  # No shared session - tasks create their own
            max_concurrent=5,
        )
        print("✅ WorkerService initialized")
        print(f"📡 Queue: {worker_service._queue_url}")
        print("🔄 Max concurrent tasks: 5")

        # Setup graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler(sig, frame):
            """Handle shutdown signals."""
            logger.info("shutdown_signal_received", signal=sig)
            shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("✅ GapSense Worker ready!")

        # Start the worker in a task
        worker_task = asyncio.create_task(worker_service.start())

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Graceful shutdown
        print("🛑 GapSense Worker shutting down...")
        await worker_service.stop()
        worker_task.cancel()

        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    except Exception as e:
        print(f"❌ WorkerService initialization failed: {e}")
        raise

    # Cleanup
    if ai_client:
        await ai_client.close()
        print("✅ AI client connection pool closed")

    from gapsense.core.database import close_db

    await close_db()
    print("✅ Worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("worker_fatal_error", error=str(e))
        print(f"❌ Worker failed: {e}")
        sys.exit(1)
