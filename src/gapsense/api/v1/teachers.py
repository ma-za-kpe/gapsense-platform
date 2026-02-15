"""
Teacher API Endpoints

Teacher management for school-based diagnostic delivery.
"""
# ruff: noqa: B008 - FastAPI Depends in function defaults is standard pattern

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gapsense.core.database import get_db
from gapsense.core.models import School, Student, Teacher
from gapsense.core.schemas import TeacherCreate, TeacherSchema, TeacherUpdate

router = APIRouter()


@router.post("/", response_model=TeacherSchema, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    teacher_data: TeacherCreate, db: AsyncSession = Depends(get_db)
) -> Teacher:
    """Create a new teacher account."""
    # Verify school exists
    result = await db.execute(select(School).where(School.id == teacher_data.school_id))
    school = result.scalar_one_or_none()

    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"School not found with ID: {teacher_data.school_id}",
        )

    # Check if phone already exists for this school
    result = await db.execute(
        select(Teacher).where(
            Teacher.school_id == teacher_data.school_id, Teacher.phone == teacher_data.phone
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Teacher already exists with phone {teacher_data.phone} at this school",
        )

    # Create teacher
    teacher = Teacher(
        school_id=teacher_data.school_id,
        first_name=teacher_data.first_name,
        last_name=teacher_data.last_name,
        phone=teacher_data.phone,
        grade_taught=teacher_data.grade_taught,
        subjects=teacher_data.subjects,
        is_active=True,
    )

    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)

    return teacher


@router.get("/{teacher_id}", response_model=TeacherSchema)
async def get_teacher(teacher_id: UUID, db: AsyncSession = Depends(get_db)) -> Teacher:
    """Get teacher details by ID."""
    result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id, Teacher.deleted_at.is_(None))
    )
    teacher = result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher not found with ID: {teacher_id}",
        )

    return teacher


@router.put("/{teacher_id}", response_model=TeacherSchema)
async def update_teacher(
    teacher_id: UUID, teacher_update: TeacherUpdate, db: AsyncSession = Depends(get_db)
) -> Teacher:
    """Update teacher information.

    Only updates fields that are explicitly provided (not None).
    """
    result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id, Teacher.deleted_at.is_(None))
    )
    teacher = result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher not found with ID: {teacher_id}",
        )

    # Update only provided fields
    update_data = teacher_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(teacher, field, value)

    await db.commit()
    await db.refresh(teacher)

    return teacher


@router.get("/{teacher_id}/students", response_model=list[dict[str, str]])
async def list_teacher_students(
    teacher_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[dict[str, str]]:
    """List all students assigned to this teacher."""
    # Verify teacher exists
    teacher_result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id, Teacher.deleted_at.is_(None))
    )
    teacher = teacher_result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher not found with ID: {teacher_id}",
        )

    # Get students
    result = await db.execute(
        select(Student)
        .where(Student.teacher_id == teacher_id)
        .options(selectinload(Student.school))
    )
    students = result.scalars().all()

    # Return student info
    return [
        {
            "id": str(student.id),
            "first_name": student.first_name,
            "grade": student.current_grade,
            "school": student.school.name if student.school else "Unknown",
        }
        for student in students
    ]


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teacher(teacher_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Soft delete a teacher.

    Sets deleted_at timestamp, preserving historical data.
    """
    result = await db.execute(
        select(Teacher).where(Teacher.id == teacher_id, Teacher.deleted_at.is_(None))
    )
    teacher = result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher not found with ID: {teacher_id}",
        )

    # Soft delete
    teacher.deleted_at = datetime.utcnow()
    teacher.is_active = False

    await db.commit()
