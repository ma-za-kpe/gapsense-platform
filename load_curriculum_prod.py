#!/usr/bin/env python3
"""
Load curriculum into production database using CurriculumLoader service.

This script loads the multi-country curriculum data from data/curricula/
into the PostgreSQL database.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gapsense.config import settings
from gapsense.core.database import AsyncSessionLocal
from gapsense.services.curriculum_loader import CurriculumLoader


async def main():
    """Load curriculum for Ghana."""
    print("🚀 Loading curriculum into production database")
    print(f"📁 Curricula path: {settings.curricula_base_path}")
    print(f"🗄️  Database: production\n")

    async with AsyncSessionLocal() as session:
        loader = CurriculumLoader(db_session=session, settings=settings)

        # Load Ghana curriculum (expand to other countries later)
        print("📖 Loading Ghana curriculum...")
        summary = await loader.load_country("ghana")

        print("\n✅ Load complete!")
        print(f"📊 Files processed: {summary.total_files}")
        print(f"📊 Nodes created: {summary.total_nodes_created}")
        print(f"📊 Nodes updated: {summary.total_nodes_updated}")
        print(f"📊 Errors: {summary.total_errors}")

        if summary.total_errors > 0:
            print("⚠️  Some errors occurred during loading")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
