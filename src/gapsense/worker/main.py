"""
GapSense Worker Service — Background Task Processor

Minimal placeholder that keeps the container alive.
Will be replaced with full SQS consumer in Task 10.1.
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the worker service and wait indefinitely."""
    logger.info("Worker service starting...")
    logger.info("Waiting for tasks (placeholder — full SQS consumer coming in Task 10.1)")
    try:
        # Keep the process alive without burning CPU
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Worker service shutting down.")


if __name__ == "__main__":
    asyncio.run(main())
