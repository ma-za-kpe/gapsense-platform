"""
Diagnostic API Endpoints

Adaptive diagnostic sessions, answer submission, and gap profiles.
"""
# ruff: noqa: B008 - FastAPI Depends in function defaults is standard pattern

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import (
    CurriculumNode,
    DiagnosticQuestion,
    DiagnosticSession,
    GapProfile,
    Student,
)
from gapsense.core.schemas.diagnostics import (
    DiagnosticAnswerResponse,
    DiagnosticAnswerSubmit,
    DiagnosticSessionCreate,
    DiagnosticSessionSchema,
    GapProfileSchema,
)
from gapsense.diagnostic import (
    AdaptiveDiagnosticEngine,
    GapProfileAnalyzer,
    QuestionGenerator,
    ResponseAnalyzer,
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
) -> dict[str, str | bool | dict[str, str | int | None] | None]:
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

    # Create diagnostic question record
    question = DiagnosticQuestion(
        session_id=session.id,
        question_order=session.total_questions + 1,
        node_id=answer_data.node_id,
        question_text="[Question recorded]",  # Will be populated properly in future
        question_type="free_response",
        student_response=answer_data.student_response,
        is_correct=answer_data.is_correct,
        response_time_seconds=answer_data.response_time_seconds,
        response_media_url=answer_data.response_media_url,
        answered_at=datetime.utcnow(),
    )
    db.add(question)

    # Get student and node for AI analysis
    student_result = await db.execute(select(Student).where(Student.id == session.student_id))
    student = student_result.scalar_one()

    node_result = await db.execute(
        select(CurriculumNode).where(CurriculumNode.id == answer_data.node_id)
    )
    node = node_result.scalar_one()

    # AI Response Analysis (DIAG-002)
    # Analyzes answer for error patterns, misconceptions, and next action
    response_analyzer = ResponseAnalyzer(use_ai=True)
    ai_analysis = response_analyzer.analyze_response(
        student=student,
        session=session,
        question=question,
        node_code=node.code,
    )

    # Store AI analysis in question record
    question.ai_analysis = ai_analysis

    # Use AI-determined correctness only if we have a real question (not placeholder)
    # This ensures we don't override user-provided correctness for placeholder questions
    if (
        question.question_text != "[Question recorded]"
        and ai_analysis.get("is_correct") is not None
    ):
        question.is_correct = ai_analysis["is_correct"]
        answer_data.is_correct = ai_analysis["is_correct"]

    # Store detected error pattern and misconception
    if ai_analysis.get("error_pattern"):
        question.error_pattern_detected = ai_analysis["error_pattern"]
    if ai_analysis.get("misconception"):
        question.misconception_id = None  # TODO: Link to CurriculumMisconception table

    # Update session statistics
    session.total_questions += 1
    if answer_data.is_correct:
        session.correct_answers += 1

    # Initialize adaptive engine
    engine = AdaptiveDiagnosticEngine(session, db)

    # Update session state based on answer
    await engine.update_session_state(answer_data.node_id, answer_data.is_correct)

    # Check if session should complete
    should_complete = await engine.should_complete_session()

    if should_complete:
        # Complete session and generate gap profile
        session.status = "completed"
        session.completed_at = datetime.utcnow()

        # Generate gap profile
        analyzer = GapProfileAnalyzer(session, db)
        gap_profile = await analyzer.generate_gap_profile()
        db.add(gap_profile)

        await db.commit()
        await db.refresh(question)

        return {
            "question_id": str(question.id),
            "is_correct": answer_data.is_correct,
            "student_response": answer_data.student_response,
            "next_question": None,
            "session_completed": True,
            "message": "Diagnostic complete. Gap profile generated.",
        }

    # Get next node to test
    next_node = await engine.get_next_node()

    if not next_node:
        # No more nodes to test - complete session
        session.status = "completed"
        session.completed_at = datetime.utcnow()

        analyzer = GapProfileAnalyzer(session, db)
        gap_profile = await analyzer.generate_gap_profile()
        db.add(gap_profile)

        await db.commit()
        await db.refresh(question)

        return {
            "question_id": str(question.id),
            "is_correct": answer_data.is_correct,
            "student_response": answer_data.student_response,
            "next_question": None,
            "session_completed": True,
            "message": "Diagnostic complete. No more nodes to test.",
        }

    # Generate next question
    question_gen = QuestionGenerator()
    next_question_data = question_gen.generate_question(next_node, session.total_questions)

    # Commit current progress
    await db.commit()
    await db.refresh(question)

    # Build next question response
    return {
        "question_id": str(question.id),
        "is_correct": answer_data.is_correct,
        "student_response": answer_data.student_response,
        "next_question": {
            "id": "00000000-0000-0000-0000-000000000000",  # Placeholder - will be created on next submit
            "session_id": str(session.id),
            "question_order": session.total_questions + 1,
            "node_id": str(next_node.id),
            "question_text": next_question_data["question_text"],
            "question_type": next_question_data["question_type"],
            "question_media_url": next_question_data["question_media_url"],
            "student_response": None,
            "is_correct": None,
            "response_time_seconds": None,
            "asked_at": datetime.utcnow().isoformat(),
            "answered_at": None,
        },
        "session_completed": False,
        "message": f"Question {session.total_questions} recorded. Continue diagnostic.",
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
