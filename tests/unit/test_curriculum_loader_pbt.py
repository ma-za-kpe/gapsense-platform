"""
Property-based tests for CurriculumLoader.

# Feature: mvp-core-services, Property 7: Curriculum Loader Path-to-Column Mapping
# Feature: mvp-core-services, Property 8: Curriculum Loader Idempotence
# Feature: mvp-core-services, Property 9: Curriculum Loader Error Resilience
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models.curriculum import CurriculumNode, CurriculumStrand, CurriculumSubStrand
from gapsense.services.curriculum_loader import CurriculumLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(base_path: Path) -> MagicMock:
    mock = MagicMock()
    type(mock).curricula_base_path = PropertyMock(return_value=base_path)
    return mock


def _write_curriculum_file(
    base: Path,
    country: str,
    level: str,
    subject: str,
    nodes: dict,
    filename: str = "populated_nodes_complete.json",
) -> Path:
    dir_path = base / country / level / subject
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename
    file_path.write_text(json.dumps(nodes))
    return file_path


async def _ensure_strand_and_substrand(session: AsyncSession) -> None:
    """Ensure strand_id=1 and sub_strand_id=1 exist for FK constraints."""
    result = await session.execute(select(CurriculumStrand).where(CurriculumStrand.id == 1))
    if result.scalar_one_or_none() is None:
        session.add(CurriculumStrand(id=1, strand_number=1, name="Number"))
        await session.flush()

    result = await session.execute(select(CurriculumSubStrand).where(CurriculumSubStrand.id == 1))
    if result.scalar_one_or_none() is None:
        session.add(
            CurriculumSubStrand(
                id=1, strand_id=1, sub_strand_number=1, phase="B1_B3", name="Counting"
            )
        )
        await session.flush()
    await session.commit()


# ---------------------------------------------------------------------------
# Property 7: Curriculum Loader Path-to-Column Mapping
# **Validates: Requirements 5.1, 5.2, 5.3**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    country=st.sampled_from(["GH", "UG", "KE", "NG"]),
    level=st.sampled_from(["primary", "secondary"]),
    subject=st.sampled_from(["mathematics", "english", "science"]),
)
async def test_curriculum_path_to_column_mapping(
    db_session: AsyncSession,
    country: str,
    level: str,
    subject: str,
):
    """Property 7: Curriculum Loader Path-to-Column Mapping

    For any file at curricula/{country}/{level}/{subject}/file.json,
    loaded CurriculumNodes have correct country, level, subject from path.
    """
    await _ensure_strand_and_substrand(db_session)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        code = "B2.1.1.1"
        nodes = {
            code: {
                "title": "Test Node",
                "description": "Test description",
                "severity": 3,
                "strand_id": 1,
                "sub_strand_id": 1,
            }
        }
        _write_curriculum_file(base, country, level, subject, nodes)

        settings_mock = _make_settings(base)
        loader = CurriculumLoader(db_session, settings_mock)
        summary = await loader.load_all_countries()
        await db_session.commit()

        result = await db_session.execute(
            select(CurriculumNode).where(
                CurriculumNode.code == code,
                CurriculumNode.country == country,
            )
        )
        node = result.scalar_one_or_none()

        assert node is not None, f"Node {code} not found for country {country}"
        assert node.country == country
        assert node.level == level
        assert node.subject == subject

        # Cleanup
        if node:
            await db_session.delete(node)
            await db_session.commit()


# ---------------------------------------------------------------------------
# Property 8: Curriculum Loader Idempotence
# **Validates: Requirements 5.5**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(
    max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_nodes=st.integers(min_value=1, max_value=5),
)
async def test_curriculum_loader_idempotence(
    db_session: AsyncSession,
    num_nodes: int,
):
    """Property 8: Curriculum Loader Idempotence

    Loading the same files twice produces same row count as loading once;
    second load yields zero new nodes.
    """
    await _ensure_strand_and_substrand(db_session)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        nodes = {}
        for i in range(num_nodes):
            code = f"B{i+1}.1.1.1"
            nodes[code] = {
                "title": f"Node {i}",
                "description": f"Description {i}",
                "severity": 3,
                "strand_id": 1,
                "sub_strand_id": 1,
            }
        _write_curriculum_file(base, "GH", "primary", "mathematics", nodes)

        settings_mock = _make_settings(base)

        # First load
        loader1 = CurriculumLoader(db_session, settings_mock)
        summary1 = await loader1.load_all_countries()
        await db_session.commit()

        first_count = summary1.total_nodes_created

        # Second load (same data)
        loader2 = CurriculumLoader(db_session, settings_mock)
        summary2 = await loader2.load_all_countries()
        await db_session.commit()

        assert (
            summary2.total_nodes_created == 0
        ), f"Second load created {summary2.total_nodes_created} new nodes, expected 0"
        assert summary2.total_nodes_updated == first_count

        # Verify total row count
        result = await db_session.execute(
            select(CurriculumNode).where(CurriculumNode.country == "GH")
        )
        all_nodes = result.scalars().all()
        assert len(all_nodes) == num_nodes

        # Cleanup
        for n in all_nodes:
            await db_session.delete(n)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Property 9: Curriculum Loader Error Resilience
# **Validates: Requirements 5.6, 5.7**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(
    max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_valid=st.integers(min_value=1, max_value=3),
    num_invalid=st.integers(min_value=1, max_value=3),
)
async def test_curriculum_loader_error_resilience(
    db_session: AsyncSession,
    num_valid: int,
    num_invalid: int,
):
    """Property 9: Curriculum Loader Error Resilience

    For any mix of valid and invalid JSON files, all valid files are processed
    and total_errors equals number of invalid files.
    """
    await _ensure_strand_and_substrand(db_session)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Write valid files in different subjects (each with populated_nodes_complete.json)
        total_valid_nodes = 0
        for i in range(num_valid):
            subject = f"subject_valid_{i}"
            dir_path = base / "GH" / "primary" / subject
            dir_path.mkdir(parents=True, exist_ok=True)
            code = f"B{i+1}.1.1.1"
            data = {
                code: {
                    "title": f"Valid Node {i}",
                    "description": f"Valid {i}",
                    "severity": 3,
                    "strand_id": 1,
                    "sub_strand_id": 1,
                }
            }
            (dir_path / "populated_nodes_complete.json").write_text(json.dumps(data))
            total_valid_nodes += 1

        # Write invalid files in different subjects (each with populated_nodes_complete.json)
        for i in range(num_invalid):
            subject = f"subject_invalid_{i}"
            dir_path = base / "GH" / "primary" / subject
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / "populated_nodes_complete.json").write_text("{{not valid json!!")

        settings_mock = _make_settings(base)
        loader = CurriculumLoader(db_session, settings_mock)
        summary = await loader.load_all_countries()
        await db_session.commit()

        assert summary.total_errors == num_invalid
        assert summary.total_files == num_valid + num_invalid
        assert summary.total_nodes_created == total_valid_nodes

        # Cleanup
        result = await db_session.execute(
            select(CurriculumNode).where(CurriculumNode.country == "GH")
        )
        for n in result.scalars().all():
            await db_session.delete(n)
        await db_session.commit()
