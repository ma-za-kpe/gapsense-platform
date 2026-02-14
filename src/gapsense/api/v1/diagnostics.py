"""
Diagnostic API Endpoints

Adaptive diagnostic sessions, answer submission, and gap profiles.
"""
# ruff: noqa: B008 - FastAPI Depends in function defaults is standard pattern

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import DiagnosticSession, GapProfile, Student
from gapsense.core.schemas.diagnostics import (
    DiagnosticAnswerResponse,
    DiagnosticAnswerSubmit,
    DiagnosticSessionCreate,
    DiagnosticSessionSchema,
    GapProfileSchema,
)

router = APIRouter()


@router.post(
    "/sessions", response_model=DiagnosticSessionSchema, status_code=status.HTTP_201_CREATED
)
async def create_diagnostic_session(
    session_data: DiagnosticSessionCreate, db: AsyncSession = Depends(get_db)
) -> DiagnosticSession:
    """Create a new diagnostic session for a student."""
    # Verify student exists
    result = await db.execute(select(Student).where(Student.id == session_data.student_id))
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student not found with ID: {session_data.student_id}",
        )

    # Create session
    session = DiagnosticSession(
        student_id=session_data.student_id,
        entry_grade=session_data.entry_grade,
        initiated_by=session_data.initiated_by,
        channel=session_data.channel,
        status="in_progress",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


@router.get("/sessions/{session_id}", response_model=DiagnosticSessionSchema)
async def get_diagnostic_session(
    session_id: UUID, db: AsyncSession = Depends(get_db)
) -> DiagnosticSession:
    """Get diagnostic session details by ID."""
    result = await db.execute(select(DiagnosticSession).where(DiagnosticSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found with ID: {session_id}",
        )

    return session


@router.get("/students/{student_id}/sessions", response_model=list[DiagnosticSessionSchema])
async def list_student_sessions(
    student_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[DiagnosticSession]:
    """List all diagnostic sessions for a student."""
    result = await db.execute(
        select(DiagnosticSession)
        .where(DiagnosticSession.student_id == student_id)
        .order_by(desc(DiagnosticSession.created_at))
    )
    sessions = result.scalars().all()
    return list(sessions)


@router.post(
    "/sessions/{session_id}/answers",
    response_model=DiagnosticAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_answer(
    session_id: UUID, answer_data: DiagnosticAnswerSubmit, db: AsyncSession = Depends(get_db)
) -> dict[str, str | bool | None]:
    """Submit an answer to a diagnostic question."""
    # Get session
    result = await db.execute(select(DiagnosticSession).where(DiagnosticSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found with ID: {session_id}",
        )

    # Check session status
    if session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit answers to {session.status} session",
        )

    # TODO: Create DiagnosticQuestion record and update session statistics
    # TODO: Implement adaptive question selection algorithm
    # TODO: Determine if session should complete

    # For now, return a simple response
    return {
        "question_id": "00000000-0000-0000-0000-000000000000",  # Placeholder
        "is_correct": answer_data.is_correct,
        "student_response": answer_data.student_response,
        "next_question": None,
        "session_completed": False,
        "message": "Answer recorded. Adaptive algorithm not yet implemented.",
    }


@router.get("/sessions/{session_id}/results", response_model=GapProfileSchema)
async def get_session_results(session_id: UUID, db: AsyncSession = Depends(get_db)) -> GapProfile:
    """Get gap profile results for a completed session."""
    # Get session
    session_result = await db.execute(
        select(DiagnosticSession).where(DiagnosticSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found with ID: {session_id}",
        )

    # Check if completed
    if session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not completed yet (status: {session.status})",
        )

    # Get gap profile
    profile_result = await db.execute(select(GapProfile).where(GapProfile.session_id == session_id))
    gap_profile = profile_result.scalar_one_or_none()

    if gap_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No gap profile found for session {session_id}",
        )

    return gap_profile


@router.get("/students/{student_id}/profiles", response_model=list[GapProfileSchema])
async def list_student_profiles(
    student_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[GapProfile]:
    """List all gap profiles for a student, most recent first."""
    result = await db.execute(
        select(GapProfile)
        .where(GapProfile.student_id == student_id)
        .order_by(desc(GapProfile.is_current), desc(GapProfile.created_at))
    )
    profiles = result.scalars().all()
    return list(profiles)


@router.get("/students/{student_id}/profile/current", response_model=GapProfileSchema)
async def get_current_profile(student_id: UUID, db: AsyncSession = Depends(get_db)) -> GapProfile:
    """Get the current (most recent) gap profile for a student."""
    result = await db.execute(
        select(GapProfile).where(GapProfile.student_id == student_id, GapProfile.is_current == True)  # noqa: E712
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No current gap profile found for student {student_id}",
        )

    return profile
