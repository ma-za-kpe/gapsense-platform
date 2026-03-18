"""
Parent API Endpoints

WhatsApp parent management following Wolf/Aurino dignity-first principles.
"""
# ruff: noqa: B008 - FastAPI Depends in function defaults is standard pattern

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gapsense.core.database import get_db
from gapsense.core.models import Parent, Student
from gapsense.core.schemas import ParentCreate, ParentSchema, ParentUpdate

router = APIRouter()


@router.post("/", response_model=ParentSchema, status_code=status.HTTP_201_CREATED)
async def create_parent(parent_data: ParentCreate, db: AsyncSession = Depends(get_db)) -> Parent:
    """Create a new parent account.

    Dignity-first onboarding - minimal data required.
    """
    # Check if phone already exists
    result = await db.execute(select(Parent).where(Parent.phone == parent_data.phone))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parent already exists with phone: {parent_data.phone}",
        )

    # Create parent
    parent = Parent(
        phone=parent_data.phone,
        preferred_name=parent_data.preferred_name,
        preferred_language=parent_data.preferred_language,
        district_id=parent_data.district_id,
        community=parent_data.community,
        opted_in=parent_data.opted_in,
        opted_in_at=datetime.utcnow() if parent_data.opted_in else None,
        is_active=True,
    )

    db.add(parent)
    await db.commit()
    await db.refresh(parent)

    return parent


@router.get("/{parent_id}", response_model=ParentSchema)
async def get_parent(parent_id: UUID, db: AsyncSession = Depends(get_db)) -> Parent:
    """Get parent details by ID."""
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent not found with ID: {parent_id}",
        )

    return parent


@router.get("/phone/{phone}", response_model=ParentSchema)
async def get_parent_by_phone(phone: str, db: AsyncSession = Depends(get_db)) -> Parent:
    """Get parent by phone number (WhatsApp identifier)."""
    result = await db.execute(select(Parent).where(Parent.phone == phone))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent not found with phone: {phone}",
        )

    return parent


@router.put("/{parent_id}", response_model=ParentSchema)
async def update_parent(
    parent_id: UUID, parent_update: ParentUpdate, db: AsyncSession = Depends(get_db)
) -> Parent:
    """Update parent information.

    Only updates fields that are explicitly provided (not None).
    """
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent not found with ID: {parent_id}",
        )

    # Update only provided fields
    update_data = parent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(parent, field, value)

    await db.commit()
    await db.refresh(parent)

    return parent


@router.get("/{parent_id}/students", response_model=list[dict[str, str]])
async def list_parent_students(
    parent_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[dict[str, str]]:
    """List all students linked to this parent."""
    # Verify parent exists
    parent_result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = parent_result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent not found with ID: {parent_id}",
        )

    # Get students where parent is primary or secondary
    result = await db.execute(
        select(Student)
        .where(
            (Student.primary_parent_id == parent_id) | (Student.secondary_parent_id == parent_id)
        )
        .options(selectinload(Student.school))
    )
    students = result.scalars().all()

    # Return minimal student info
    return [
        {
            "id": str(student.id),
            "first_name": student.first_name,
            "grade": student.current_grade,
            "school": student.school.name if student.school else "Unknown",
        }
        for student in students
    ]


@router.post("/{parent_id}/opt-out", response_model=ParentSchema)
async def opt_out_parent(parent_id: UUID, db: AsyncSession = Depends(get_db)) -> Parent:
    """Handle parent opt-out from WhatsApp engagement.

    Wolf/Aurino compliance - immediate and complete opt-out.
    """
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent not found with ID: {parent_id}",
        )

    # Mark as opted out
    parent.opted_out = True
    parent.opted_out_at = datetime.utcnow()
    parent.opted_in = False
    parent.is_active = False

    await db.commit()
    await db.refresh(parent)

    return parent


@router.post("/{parent_id}/opt-in", response_model=ParentSchema)
async def opt_in_parent(parent_id: UUID, db: AsyncSession = Depends(get_db)) -> Parent:
    """Re-opt-in parent to WhatsApp engagement."""
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent not found with ID: {parent_id}",
        )

    # Mark as opted in
    parent.opted_in = True
    parent.opted_in_at = datetime.utcnow()
    parent.opted_out = False
    parent.is_active = True

    await db.commit()
    await db.refresh(parent)

    return parent
