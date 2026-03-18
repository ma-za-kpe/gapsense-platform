#!/usr/bin/env python3
"""
Indicator & Error Pattern Loader: populated_nodes JSON → PostgreSQL

Reads the populated nodes JSON (with indicators and error patterns) and loads
them into the curriculum_indicators and indicator_error_patterns tables.

Usage:
    python scripts/load_indicators.py                # Load from default path
    python scripts/load_indicators.py --reload       # Delete indicators/errors and reload
    python scripts/load_indicators.py --path=/custom/path.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gapsense.config import settings
from gapsense.core.models import (
    CurriculumIndicator,
    CurriculumNode,
    IndicatorErrorPattern,
)
from gapsense.core.models.base import Base

# Default data path (works both inside Docker at /app and outside)
DEFAULT_DATA_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "curricula"
    / "ghana"
    / "primary"
    / "mathematics"
    / "populated_nodes_complete.json"
)


class IndicatorLoader:
    """Loads indicators and error patterns from populated nodes JSON into PostgreSQL."""

    def __init__(self, db_url: str, data_path: Path):
        self.db_url = db_url
        self.data_path = data_path
        self.engine = create_async_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create_tables(self) -> None:
        """Create all tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables verified")

    async def delete_existing(self) -> None:
        """Delete existing indicators and error patterns (for --reload)."""
        async with self.SessionLocal() as session:
            # Delete in dependency order: error patterns first, then indicators
            await session.execute(IndicatorErrorPattern.__table__.delete())
            await session.execute(CurriculumIndicator.__table__.delete())
            await session.commit()
        print("🗑️  Deleted existing indicators and error patterns")

    async def load_indicators(self) -> None:
        """Main loading orchestrator."""
        print(f"📖 Reading populated nodes from: {self.data_path}")

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Populated nodes file not found: {self.data_path}\n"
                f"Make sure the data directory contains the populated nodes JSON."
            )

        with open(self.data_path, encoding="utf-8") as f:
            data = json.load(f)

        nodes_data = data.get("nodes_fully_populated", {})
        print(f"📊 Nodes in file: {len(nodes_data)}")

        total_indicators_in_file = sum(
            len(node_info.get("indicators", {})) for node_info in nodes_data.values()
        )
        print(f"📊 Total indicators in file: {total_indicators_in_file}")

        indicators_added = 0
        indicators_skipped = 0
        errors_added = 0
        nodes_found = 0
        nodes_missing = 0

        async with self.SessionLocal() as session:
            for node_code, node_info in nodes_data.items():
                # Look up the node by code in the DB
                result = await session.execute(
                    select(CurriculumNode.id).where(CurriculumNode.code == node_code)
                )
                node_id = result.scalar_one_or_none()

                if node_id is None:
                    print(f"  ⚠️  Node {node_code} not found in DB — skipping")
                    nodes_missing += 1
                    continue

                nodes_found += 1
                indicators = node_info.get("indicators", {})

                for indicator_code, indicator_info in indicators.items():
                    # Check if indicator already exists (idempotent)
                    result = await session.execute(
                        select(CurriculumIndicator.id).where(
                            CurriculumIndicator.indicator_code == indicator_code
                        )
                    )
                    existing_id = result.scalar_one_or_none()

                    if existing_id is not None:
                        indicators_skipped += 1
                        continue

                    # Create the indicator
                    indicator_id = uuid4()
                    indicator = CurriculumIndicator(
                        id=indicator_id,
                        node_id=node_id,
                        indicator_code=indicator_code,
                        title=indicator_info["title"],
                        diagnostic_question_type=indicator_info.get("diagnostic_question_type"),
                        diagnostic_prompt_example=indicator_info.get("diagnostic_prompt_example"),
                    )
                    session.add(indicator)
                    indicators_added += 1

                    # Create error patterns for this indicator
                    error_patterns = indicator_info.get("error_patterns", [])
                    for error_desc in error_patterns:
                        # Determine severity: "CRITICAL:" prefix → critical
                        severity = "standard"
                        if error_desc.startswith("CRITICAL:"):
                            severity = "critical"

                        error_pattern = IndicatorErrorPattern(
                            indicator_id=indicator_id,
                            error_description=error_desc,
                            severity=severity,
                        )
                        session.add(error_pattern)
                        errors_added += 1

                # Flush after each node to keep memory manageable
                await session.flush()
                print(f"  📌 {node_code}: loaded {len(indicators)} indicators")

            await session.commit()

        # Summary
        print("\n📊 Load Summary:")
        print(f"  Nodes found:         {nodes_found}")
        print(f"  Nodes missing:       {nodes_missing}")
        print(f"  Indicators added:    {indicators_added}")
        print(f"  Indicators skipped:  {indicators_skipped} (already existed)")
        print(f"  Error patterns added: {errors_added}")

    async def verify_load(self) -> None:
        """Verify data was loaded correctly."""
        async with self.SessionLocal() as session:
            indicator_rows = (await session.execute(select(CurriculumIndicator))).scalars().all()
            error_rows = (await session.execute(select(IndicatorErrorPattern))).scalars().all()

            print("\n📊 Database Verification:")
            print(f"  Indicators in DB:     {len(indicator_rows)}")
            print(f"  Error patterns in DB: {len(error_rows)}")

            if indicator_rows:
                sample = indicator_rows[0]
                print(f"\n📝 Sample Indicator: {sample.indicator_code} — {sample.title}")
                print(f"  Question type: {sample.diagnostic_question_type}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load curriculum indicators and error patterns from JSON to PostgreSQL"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Delete existing indicators/error patterns before loading",
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Custom path to populated nodes JSON",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Custom database URL (default from settings)",
    )
    args = parser.parse_args()

    # Determine paths
    db_url = args.db_url or settings.DATABASE_URL
    data_path = args.path or DEFAULT_DATA_PATH

    print("🚀 GapSense Indicator Loader")
    print(f"📁 Data: {data_path}")
    print(f"🗄️  Database: {db_url.split('@')[1] if '@' in db_url else db_url}\n")

    loader = IndicatorLoader(db_url, data_path)

    try:
        # Create tables
        await loader.create_tables()

        # Delete existing if --reload
        if args.reload:
            print("⚠️  RELOAD mode: Deleting existing indicators and error patterns...")
            await loader.delete_existing()

        # Load data
        await loader.load_indicators()

        # Verify
        await loader.verify_load()

        print("\n✅ Load complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        await loader.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
