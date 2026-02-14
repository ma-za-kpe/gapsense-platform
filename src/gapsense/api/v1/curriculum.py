"""
Curriculum API Endpoints

Provides read-only access to curriculum data (strands, sub-strands, nodes).
"""
# ruff: noqa: B008 - FastAPI Depends in function defaults is standard pattern

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gapsense.core.database import get_db
from gapsense.core.models import (
    CurriculumNode,
    CurriculumPrerequisite,
    CurriculumStrand,
)
from gapsense.core.schemas.curriculum import (
    CurriculumNodeDetailSchema,
    CurriculumNodeSchema,
    CurriculumStrandDetailSchema,
    CurriculumStrandSchema,
    PrerequisiteGraphSchema,
)

router = APIRouter()


@router.get("/strands", response_model=list[CurriculumStrandSchema])
async def list_strands(db: AsyncSession = Depends(get_db)) -> list[CurriculumStrand]:
    """List all curriculum strands."""
    result = await db.execute(select(CurriculumStrand).order_by(CurriculumStrand.strand_number))
    strands = result.scalars().all()
    return list(strands)


@router.get("/strands/{strand_id}", response_model=CurriculumStrandDetailSchema)
async def get_strand(strand_id: int, db: AsyncSession = Depends(get_db)) -> CurriculumStrand:
    """Get a specific curriculum strand with sub-strands."""
    result = await db.execute(
        select(CurriculumStrand)
        .where(CurriculumStrand.id == strand_id)
        .options(selectinload(CurriculumStrand.sub_strands))
    )
    strand = result.scalar_one_or_none()

    if not strand:
        raise HTTPException(status_code=404, detail="Strand not found")

    return strand


@router.get("/nodes", response_model=list[CurriculumNodeSchema])
async def list_nodes(
    grade: str | None = Query(None, description="Filter by grade (e.g., B1, B2)"),
    min_severity: int | None = Query(None, ge=1, le=5, description="Minimum severity level"),
    db: AsyncSession = Depends(get_db),
) -> list[CurriculumNode]:
    """List curriculum nodes with optional filtering."""
    query = select(CurriculumNode)

    if grade:
        query = query.where(CurriculumNode.grade == grade)

    if min_severity:
        query = query.where(CurriculumNode.severity >= min_severity)

    query = query.order_by(CurriculumNode.code)

    result = await db.execute(query)
    nodes = result.scalars().all()
    return list(nodes)


@router.get("/nodes/{code}", response_model=CurriculumNodeDetailSchema)
async def get_node(code: str, db: AsyncSession = Depends(get_db)) -> CurriculumNode:
    """Get a specific curriculum node by code."""
    result = await db.execute(
        select(CurriculumNode)
        .where(CurriculumNode.code == code)
        .options(selectinload(CurriculumNode.strand), selectinload(CurriculumNode.sub_strand))
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    return node


@router.get("/nodes/{code}/prerequisites", response_model=PrerequisiteGraphSchema)
async def get_node_prerequisites(
    code: str, db: AsyncSession = Depends(get_db)
) -> dict[str, CurriculumNode | list[CurriculumNode]]:
    """Get prerequisite tree for a curriculum node."""
    # Get the node
    result = await db.execute(select(CurriculumNode).where(CurriculumNode.code == code))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Get prerequisites (target nodes where source = current node)
    result = await db.execute(
        select(CurriculumNode)
        .join(
            CurriculumPrerequisite,
            CurriculumPrerequisite.target_node_id == CurriculumNode.id,
        )
        .where(CurriculumPrerequisite.source_node_id == node.id)
    )
    prerequisites = result.scalars().all()

    return {"node": node, "prerequisites": list(prerequisites)}
