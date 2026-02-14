#!/usr/bin/env python3
"""
Curriculum Loader: gapsense-data JSON → PostgreSQL

Reads the prerequisite graph JSON from gapsense-data repo and loads it into
the PostgreSQL database tables.

Usage:
    python scripts/load_curriculum.py              # Load from default path
    python scripts/load_curriculum.py --reload     # Truncate and reload
    python scripts/load_curriculum.py --path=/custom/path.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gapsense.config import settings
from gapsense.core.models import (
    CascadePath,
    CurriculumIndicator,
    CurriculumMisconception,
    CurriculumNode,
    CurriculumPrerequisite,
    CurriculumStrand,
    CurriculumSubStrand,
)
from gapsense.core.models.base import Base


class CurriculumLoader:
    """Loads prerequisite graph from JSON into PostgreSQL."""

    def __init__(self, db_url: str, graph_path: Path):
        self.db_url = db_url
        self.graph_path = graph_path
        self.engine = create_async_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        # Track node code → UUID mapping for prerequisites
        self.node_id_map: dict[str, UUID] = {}

    async def create_tables(self) -> None:
        """Create all tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created/verified")

    async def truncate_tables(self) -> None:
        """Truncate all curriculum tables (for --reload)."""
        async with self.SessionLocal() as session:
            # Delete in reverse dependency order
            await session.execute(CascadePath.__table__.delete())
            await session.execute(CurriculumMisconception.__table__.delete())
            await session.execute(CurriculumIndicator.__table__.delete())
            await session.execute(CurriculumPrerequisite.__table__.delete())
            await session.execute(CurriculumNode.__table__.delete())
            await session.execute(CurriculumSubStrand.__table__.delete())
            await session.execute(CurriculumStrand.__table__.delete())
            await session.commit()
        print("✅ Truncated all curriculum tables")

    async def load_graph(self) -> None:
        """Main loading orchestrator."""
        print(f"📖 Reading graph from: {self.graph_path}")

        if not self.graph_path.exists():
            raise FileNotFoundError(
                f"Prerequisite graph not found: {self.graph_path}\n"
                f"Make sure GAPSENSE_DATA_PATH points to gapsense-data repo."
            )

        with open(self.graph_path, encoding="utf-8") as f:
            data = json.load(f)

        print(f"📊 Graph version: {data.get('version', 'unknown')}")
        print(f"📊 Nodes: {len(data.get('nodes', []))}")
        print(f"📊 Prerequisites: {len(data.get('prerequisites', []))}")
        print(f"📊 Misconceptions: {len(data.get('misconceptions', []))}")
        print(f"📊 Cascades: {len(data.get('cascades', []))}")

        async with self.SessionLocal() as session:
            # Step 1: Load strands
            await self._load_strands(session, data.get("strands", []))

            # Step 2: Load sub-strands
            await self._load_sub_strands(session, data.get("sub_strands", []))

            # Step 3: Load nodes
            await self._load_nodes(session, data.get("nodes", []))

            # Step 4: Load prerequisites (edges)
            await self._load_prerequisites(session, data.get("prerequisites", []))

            # Step 5: Load misconceptions
            await self._load_misconceptions(session, data.get("misconceptions", []))

            # Step 6: Load cascade paths
            await self._load_cascades(session, data.get("cascades", []))

            await session.commit()

        print("✅ Curriculum loaded successfully!")

    async def _load_strands(
        self, session: AsyncSession, strands: list[dict[str, Any]] | dict[str, Any]
    ) -> None:
        """Load curriculum strands."""
        # Handle both list and dict formats
        if isinstance(strands, dict):
            strands_list = [
                {
                    "strand_number": int(k),
                    "name": v["name"],
                    "color_hex": v.get("color"),
                    "description": v.get("description"),
                }
                for k, v in strands.items()
            ]
        else:
            strands_list = strands

        for strand_data in strands_list:
            strand = CurriculumStrand(
                strand_number=strand_data["strand_number"],
                name=strand_data["name"],
                color_hex=strand_data.get("color_hex"),
                description=strand_data.get("description"),
            )
            session.add(strand)
        await session.flush()
        print(f"  ✅ Loaded {len(strands_list)} strands")

    async def _load_sub_strands(
        self, session: AsyncSession, sub_strands: list[dict[str, Any]]
    ) -> None:
        """Load curriculum sub-strands."""
        for sub_strand_data in sub_strands:
            # Look up strand_id from strand_number
            result = await session.execute(
                select(CurriculumStrand.id).where(
                    CurriculumStrand.strand_number == sub_strand_data["strand_number"]
                )
            )
            strand_id = result.scalar_one()

            sub_strand = CurriculumSubStrand(
                strand_id=strand_id,
                sub_strand_number=sub_strand_data["sub_strand_number"],
                phase=sub_strand_data["phase"],
                name=sub_strand_data["name"],
                description=sub_strand_data.get("description"),
            )
            session.add(sub_strand)
        await session.flush()
        print(f"  ✅ Loaded {len(sub_strands)} sub-strands")

    async def _load_nodes(
        self, session: AsyncSession, nodes: list[dict[str, Any]] | dict[str, Any]
    ) -> None:
        """Load curriculum nodes."""
        # Handle both list and dict formats
        if isinstance(nodes, dict):
            # Filter out non-dict values (section headers, etc.)
            nodes_list = [v for v in nodes.values() if isinstance(v, dict)]
        else:
            nodes_list = nodes

        for node_data in nodes_list:
            # Parse code to extract strand and sub-strand numbers
            # Format: B2.1.1.1 = grade.strand.substrand.content
            code_parts = node_data["code"].split(".")
            grade = f"B{code_parts[0][1:]}"  # Extract grade (B2, B3, etc.)
            strand_num = int(code_parts[1])
            sub_strand_num = int(code_parts[2])
            content_standard_num = int(code_parts[3])

            # Look up strand_id
            result = await session.execute(
                select(CurriculumStrand.id).where(CurriculumStrand.strand_number == strand_num)
            )
            strand_id = result.scalar_one()

            # Look up sub_strand_id
            # Need to match on strand_id, sub_strand_number, and phase
            phase = self._grade_to_phase(grade)
            result = await session.execute(
                select(CurriculumSubStrand.id).where(
                    CurriculumSubStrand.strand_id == strand_id,
                    CurriculumSubStrand.sub_strand_number == sub_strand_num,
                    CurriculumSubStrand.phase == phase,
                )
            )
            sub_strand_id = result.scalar_one()

            # Generate UUID for this node
            node_id = uuid4()
            self.node_id_map[node_data["code"]] = node_id

            node = CurriculumNode(
                id=node_id,
                code=node_data["code"],
                grade=grade,
                strand_id=strand_id,
                sub_strand_id=sub_strand_id,
                content_standard_number=content_standard_num,
                title=node_data["title"],
                description=node_data["description"],
                severity=node_data["severity"],
                severity_rationale=node_data.get("severity_rationale"),
                questions_required=node_data.get("questions_required", 2),
                confidence_threshold=node_data.get("confidence_threshold", 0.80),
                ghana_evidence=node_data.get("ghana_evidence"),
                population_status=node_data.get("population_status", "skeleton"),
            )
            session.add(node)

        await session.flush()
        print(f"  ✅ Loaded {len(nodes_list)} nodes")

    async def _load_prerequisites(
        self, session: AsyncSession, prerequisites: list[dict[str, Any]]
    ) -> None:
        """Load prerequisite edges."""
        for prereq_data in prerequisites:
            source_id = self.node_id_map[prereq_data["source"]]
            target_id = self.node_id_map[prereq_data["target"]]

            prereq = CurriculumPrerequisite(
                source_node_id=source_id,
                target_node_id=target_id,
                relationship=prereq_data.get("relationship", "requires"),
                weight=prereq_data.get("weight", 1.0),
                notes=prereq_data.get("notes"),
            )
            session.add(prereq)

        await session.flush()
        print(f"  ✅ Loaded {len(prerequisites)} prerequisite edges")

    async def _load_misconceptions(
        self, session: AsyncSession, misconceptions: list[dict[str, Any]]
    ) -> None:
        """Load common misconceptions."""
        for misconception_data in misconceptions:
            node_id = self.node_id_map[misconception_data["node_code"]]

            misconception = CurriculumMisconception(
                id=misconception_data["id"],
                node_id=node_id,
                description=misconception_data["description"],
                evidence=misconception_data["evidence"],
                root_cause=misconception_data["root_cause"],
                remediation_approach=misconception_data["remediation_approach"],
                frequency_estimate=misconception_data.get("frequency_estimate"),
                source_citation=misconception_data.get("source_citation"),
            )
            session.add(misconception)

        await session.flush()
        print(f"  ✅ Loaded {len(misconceptions)} misconceptions")

    async def _load_cascades(self, session: AsyncSession, cascades: list[dict[str, Any]]) -> None:
        """Load cascade failure paths."""
        for cascade_data in cascades:
            # Convert node codes to UUIDs
            node_sequence = [self.node_id_map[code] for code in cascade_data["node_sequence"]]

            # Optional: entry point
            entry_point_id = None
            if cascade_data.get("diagnostic_entry_point"):
                entry_point_id = self.node_id_map[cascade_data["diagnostic_entry_point"]]

            cascade = CascadePath(
                name=cascade_data["name"],
                description=cascade_data["description"],
                frequency=cascade_data.get("frequency"),
                diagnostic_entry_point=entry_point_id,
                diagnostic_entry_question=cascade_data.get("diagnostic_entry_question"),
                remediation_priority=cascade_data.get("remediation_priority"),
                node_sequence=node_sequence,
            )
            session.add(cascade)

        await session.flush()
        print(f"  ✅ Loaded {len(cascades)} cascade paths")

    @staticmethod
    def _grade_to_phase(grade: str) -> str:
        """Convert grade (B1-B9) to phase (B1_B3, B4_B6, B7_B9)."""
        grade_num = int(grade[1:])
        if 1 <= grade_num <= 3:
            return "B1_B3"
        elif 4 <= grade_num <= 6:
            return "B4_B6"
        elif 7 <= grade_num <= 9:
            return "B7_B9"
        else:
            raise ValueError(f"Invalid grade: {grade}")

    async def verify_load(self) -> None:
        """Verify data was loaded correctly."""
        async with self.SessionLocal() as session:
            # Count records
            strand_count = (await session.execute(select(CurriculumStrand))).scalars().all()
            node_count = (await session.execute(select(CurriculumNode))).scalars().all()
            prereq_count = (await session.execute(select(CurriculumPrerequisite))).scalars().all()

            print("\n📊 Database Verification:")
            print(f"  Strands: {len(strand_count)}")
            print(f"  Nodes: {len(node_count)}")
            print(f"  Prerequisites: {len(prereq_count)}")

            # Sample query: Get a node with its prerequisites
            if node_count:
                sample_node = node_count[0]
                print(f"\n📝 Sample Node: {sample_node.code} - {sample_node.title}")
                print(f"  Severity: {sample_node.severity}/5")
                print(f"  Grade: {sample_node.grade}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load curriculum from JSON to PostgreSQL")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Truncate existing data before loading",
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Custom path to prerequisite graph JSON",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Custom database URL (default from settings)",
    )
    args = parser.parse_args()

    # Determine paths
    db_url = args.db_url or settings.DATABASE_URL
    graph_path = args.path or settings.prerequisite_graph_path

    print("🚀 GapSense Curriculum Loader")
    print(f"📁 Graph: {graph_path}")
    print(f"🗄️  Database: {db_url.split('@')[1] if '@' in db_url else db_url}\n")

    loader = CurriculumLoader(db_url, graph_path)

    try:
        # Create tables
        await loader.create_tables()

        # Truncate if --reload
        if args.reload:
            print("⚠️  RELOAD mode: Truncating existing data...")
            await loader.truncate_tables()

        # Load data
        await loader.load_graph()

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
