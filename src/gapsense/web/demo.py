"""
GapSense Teacher Demo Web Interface

A web-based simulation of the WhatsApp teacher flow for demos.
Uses the same backend services as the WhatsApp integration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from gapsense.core.database import get_db
from gapsense.core.models import Student, Teacher
from gapsense.core.models.diagnostics import GapProfile
from gapsense.engagement.teacher_flows import TeacherFlowExecutor
from gapsense.services.class_gap_analyzer import ClassGapAnalyzer

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])

# Template setup
import os
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def demo_page(request: Request):
    """Render the teacher demo interface."""
    return templates.TemplateResponse("demo.html", {"request": request})


@router.post("/api/message")
async def send_message(
    message: str = Form(...),
    teacher_phone: str = Form(...),
    button_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Process a teacher message (text or command).

    Simulates WhatsApp text message handling.

    Args:
        message: The text message or button title
        teacher_phone: Teacher's phone number
        button_id: If clicking a button, the button ID (makes it an interactive message)
        db: Database session
    """
    try:
        # Get or create demo teacher
        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        # Process message through TeacherFlowExecutor in demo mode
        executor = TeacherFlowExecutor(db=db, demo_mode=True)

        # Determine message type and content based on whether it's a button click
        if button_id:
            # Button click - format as interactive message
            message_type = "interactive"
            message_content = {
                "button_reply": {
                    "id": button_id,
                    "title": message
                }
            }
        else:
            # Regular text message
            message_type = "text"
            message_content = message

        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type=message_type,
            message_content=message_content,
            message_id=f"demo_{teacher_phone}_{len(message)}",
        )

        # Extract captured response from mock client
        response_text = executor.whatsapp.get_last_message() or "Message received"

        await db.refresh(teacher)

        return JSONResponse({
            "success": True,
            "response": response_text,
            "flow": result.flow_name,
            "next_step": result.next_step,
            "completed": result.completed,
            "conversation_state": teacher.conversation_state,
        })

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/upload-image")
async def upload_exercise_book(
    image: UploadFile = File(...),
    teacher_phone: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Handle exercise book image upload.

    Simulates WhatsApp image message handling.
    """
    try:
        # Get or create demo teacher
        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        # Read image bytes
        image_bytes = await image.read()

        # Create image content dict (simulating WhatsApp webhook format)
        # Include image_bytes for demo mode so real AI analysis can access it
        image_content = {
            "id": f"demo_image_{teacher_phone}",
            "mime_type": image.content_type or "image/jpeg",
            "sha256": "demo_sha256",
            "image_bytes": image_bytes,  # Pass actual image data for AI analysis
        }

        # Process through TeacherFlowExecutor in demo mode
        executor = TeacherFlowExecutor(db=db, demo_mode=True)

        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="image",
            message_content=image_content,
            message_id=f"demo_img_{teacher_phone}",
        )

        # Extract captured response
        response_text = executor.whatsapp.get_last_message() or "Image uploaded successfully"

        await db.refresh(teacher)

        return JSONResponse({
            "success": True,
            "response": response_text,
            "flow": result.flow_name,
            "next_step": result.next_step,
            "conversation_state": teacher.conversation_state,
        })

    except Exception as e:
        logger.error(f"Error uploading image: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/status")
async def get_class_status(
    teacher_phone: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get class status overview (/STATUS command)."""
    try:
        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        analyzer = ClassGapAnalyzer(db)
        overview = await analyzer.get_class_overview(teacher.id)

        # Format response
        common_gaps = [
            {
                "code": gap.node_code,
                "title": gap.node_title,
                "student_count": gap.student_count,
                "severity": gap.severity,
            }
            for gap in overview.common_gaps[:5]
        ]

        return JSONResponse({
            "success": True,
            "total_students": overview.total_students,
            "scanned_students": overview.scanned_students,
            "last_scan_date": overview.last_scan_date.isoformat() if overview.last_scan_date else None,
            "common_gaps": common_gaps,
            "improvement_percentage": overview.improvement_percentage,
        })

    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/gaps")
async def get_gap_breakdown(
    teacher_phone: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get detailed gap breakdown (/GAPS command)."""
    try:
        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        analyzer = ClassGapAnalyzer(db)
        gaps = await analyzer.get_gap_breakdown(teacher.id)

        gap_list = [
            {
                "code": gap.node_code,
                "title": gap.node_title,
                "student_count": gap.student_count,
                "severity": gap.severity,
            }
            for gap in gaps
        ]

        return JSONResponse({
            "success": True,
            "gaps": gap_list,
        })

    except Exception as e:
        logger.error(f"Error getting gaps: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/student/{student_name}")
async def get_student_report(
    student_name: str,
    teacher_phone: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get individual student report (/STUDENT command)."""
    try:
        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        # Find student
        from gapsense.core.models import Student

        stmt = (
            select(Student)
            .where(Student.teacher_id == teacher.id)
            .where(Student.first_name.ilike(f"%{student_name}%"))
            .where(Student.deleted_at.is_(None))
        )
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()

        if not student:
            return JSONResponse({
                "success": False,
                "error": f"Student '{student_name}' not found"
            }, status_code=404)

        # Get report
        analyzer = ClassGapAnalyzer(db)
        report = await analyzer.get_student_report(student.id)

        if not report:
            return JSONResponse({
                "success": False,
                "error": "No report available"
            }, status_code=404)

        return JSONResponse({
            "success": True,
            "student_name": report.student_name,
            "scan_date": report.scan_date.isoformat() if report.scan_date else None,
            "primary_gap": report.primary_gap,
            "gap_list": report.gap_list,
            "recommended_actions": report.recommended_actions,
            "estimated_time": report.estimated_time,
        })

    except Exception as e:
        logger.error(f"Error getting student report: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/api/teacher-info")
async def get_teacher_info(
    teacher_phone: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Get teacher info and conversation state."""
    try:
        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        # Get student list
        from gapsense.core.models import Student

        stmt = (
            select(Student)
            .where(Student.teacher_id == teacher.id)
            .order_by(Student.first_name)
        )
        result = await db.execute(stmt)
        students = result.scalars().all()

        student_list = [
            {
                "id": str(student.id),
                "name": student.first_name or student.full_name,
                "grade": student.current_grade,
            }
            for student in students
        ]

        return JSONResponse({
            "success": True,
            "teacher": {
                "phone": teacher.phone,
                "school_name": teacher.school.name if teacher.school else None,
                "class_name": teacher.class_name,
                "onboarded": teacher.onboarded_at is not None,
            },
            "students": student_list,
            "conversation_state": teacher.conversation_state,
        })

    except Exception as e:
        logger.error(f"Error getting teacher info: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/reports/{teacher_phone}", response_class=HTMLResponse)
async def teacher_reports_dashboard(
    request: Request,
    teacher_phone: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Comprehensive teacher dashboard with exercise book analysis reports."""
    try:
        from datetime import datetime, timedelta
        from gapsense.core.models import CurriculumNode

        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        # Get all students for this teacher
        stmt = select(Student).where(Student.teacher_id == teacher.id).order_by(Student.first_name)
        result = await db.execute(stmt)
        students = result.scalars().all()

        # Calculate stats
        total_students = len(students)
        today = datetime.utcnow().date()
        scanned_today = 0
        total_gaps = 0
        high_priority = 0

        # Get latest analysis
        latest_analysis = None
        latest_profile_stmt = (
            select(GapProfile)
            .where(GapProfile.student_id.in_([s.id for s in students]))
            .where(GapProfile.is_current == True)
            .where(GapProfile.source == "exercise_book")
            .order_by(GapProfile.created_at.desc())
            .limit(1)
        )
        latest_result = await db.execute(latest_profile_stmt)
        latest_profile = latest_result.scalar_one_or_none()

        if latest_profile:
            # Get student for latest analysis
            student_stmt = select(Student).where(Student.id == latest_profile.student_id)
            student_result = await db.execute(student_stmt)
            latest_student = student_result.scalar_one_or_none()

            if latest_student:
                # Get curriculum nodes for gaps
                if latest_profile.gap_nodes:
                    nodes_stmt = select(CurriculumNode).where(CurriculumNode.id.in_(latest_profile.gap_nodes))
                    nodes_result = await db.execute(nodes_stmt)
                    gap_nodes = nodes_result.scalars().all()

                    gaps_data = [
                        {
                            "code": node.code,
                            "title": node.title,
                            "severity": "high" if node.severity >= 4 else ("medium" if node.severity >= 3 else "low"),
                        }
                        for node in gap_nodes
                    ]
                else:
                    gaps_data = []

                # Extract metadata safely (might be dict or None)
                metadata_dict = {}
                if latest_profile.analysis_metadata and isinstance(latest_profile.analysis_metadata, dict):
                    metadata_dict = latest_profile.analysis_metadata

                latest_analysis = {
                    "student_name": latest_student.first_name or latest_student.full_name,
                    "created_at": latest_profile.created_at.strftime("%B %d, %Y at %I:%M %p"),
                    "errors": metadata_dict.get("errors", []),
                    "patterns": metadata_dict.get("patterns", []),
                    "focus_areas": metadata_dict.get("focus_areas", []),
                    "gaps": gaps_data,
                }

        # Build students data with gap profiles
        students_data = []
        for student in students:
            # Get current gap profile
            profile_stmt = (
                select(GapProfile)
                .where(GapProfile.student_id == student.id)
                .where(GapProfile.is_current == True)
                .order_by(GapProfile.created_at.desc())
                .limit(1)
            )
            profile_result = await db.execute(profile_stmt)
            profile = profile_result.scalar_one_or_none()

            gaps_data = []
            scan_count = 0
            metadata_dict = {}

            if profile:
                scan_count = 1
                if profile.created_at.date() == today:
                    scanned_today += 1

                # Extract metadata safely
                if profile.analysis_metadata and isinstance(profile.analysis_metadata, dict):
                    metadata_dict = profile.analysis_metadata

                if profile.gap_nodes:
                    total_gaps += len(profile.gap_nodes)
                    # Get node details
                    nodes_stmt = select(CurriculumNode).where(CurriculumNode.id.in_(profile.gap_nodes))
                    nodes_result = await db.execute(nodes_stmt)
                    nodes = nodes_result.scalars().all()

                    for node in nodes:
                        if node.severity >= 4:
                            high_priority += 1
                        gaps_data.append({
                            "code": node.code,
                            "title": node.title,
                            "severity": "high" if node.severity >= 4 else ("medium" if node.severity >= 3 else "low"),
                        })

            students_data.append({
                "id": str(student.id),
                "first_name": student.first_name or student.full_name or "Unknown",
                "full_name": student.full_name or "",
                "grade": student.current_grade or "JHS1",
                "scan_count": scan_count,
                "last_diagnosed": profile.created_at.strftime("%b %d") if profile else None,
                "gaps": gaps_data,
                "errors": metadata_dict.get("errors", []),
                "patterns": metadata_dict.get("patterns", []),
                "focus_areas": metadata_dict.get("focus_areas", []),
            })

        stats = {
            "total_students": total_students,
            "scanned_today": scanned_today,
            "total_gaps": total_gaps,
            "high_priority": high_priority,
        }

        return templates.TemplateResponse(
            "teacher_reports.html",
            {
                "request": request,
                "teacher_name": f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() or "Demo Teacher",
                "teacher_phone": teacher_phone,
                "stats": stats,
                "latest_analysis": latest_analysis,
                "students": students_data,
            },
        )

    except Exception as e:
        logger.error(f"Error loading teacher dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{teacher_phone}/student/{student_id}", response_class=HTMLResponse)
async def student_detailed_report(
    request: Request,
    teacher_phone: str,
    student_id: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Comprehensive student detailed report with AI metadata and analysis."""
    try:
        from datetime import datetime
        from uuid import UUID
        from gapsense.core.models import CurriculumNode
        from gapsense.core.models.ai_usage import AIUsageLog
        import json

        from sqlalchemy.orm import selectinload
        from gapsense.core.models import School

        teacher = await get_or_create_demo_teacher(db, teacher_phone)

        # Get student with eager loading of school
        stmt = select(Student).options(selectinload(Student.school)).where(Student.id == UUID(student_id))
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get current gap profile
        profile_stmt = (
            select(GapProfile)
            .where(GapProfile.student_id == UUID(student_id))
            .where(GapProfile.is_current == True)
            .order_by(GapProfile.created_at.desc())
            .limit(1)
        )
        profile_result = await db.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()

        if not profile:
            raise HTTPException(status_code=404, detail="No analysis found for this student")

        # Get AI usage log for this analysis (most recent for this student)
        usage_stmt = (
            select(AIUsageLog)
            .where(AIUsageLog.student_id == UUID(student_id))
            .order_by(AIUsageLog.created_at.desc())
            .limit(1)
        )
        usage_result = await db.execute(usage_stmt)
        ai_usage = usage_result.scalar_one_or_none()

        # Get historical AI usage (last 5)
        historical_stmt = (
            select(AIUsageLog)
            .where(AIUsageLog.student_id == UUID(student_id))
            .order_by(AIUsageLog.created_at.desc())
            .limit(5)
        )
        historical_result = await db.execute(historical_stmt)
        historical_usage_logs = historical_result.scalars().all()

        # Extract metadata
        metadata_dict = {}
        if profile.analysis_metadata and isinstance(profile.analysis_metadata, dict):
            metadata_dict = profile.analysis_metadata

        # Get gap nodes details
        gap_nodes_data = []
        if profile.gap_nodes:
            nodes_stmt = select(CurriculumNode).where(CurriculumNode.id.in_(profile.gap_nodes))
            nodes_result = await db.execute(nodes_stmt)
            nodes = nodes_result.scalars().all()

            for node in nodes:
                gap_nodes_data.append({
                    "code": node.code,
                    "title": node.title,
                    "severity": "high" if node.severity >= 4 else ("medium" if node.severity >= 3 else "low"),
                })

        # Get diagnosis count
        diagnosis_count_stmt = select(GapProfile).where(GapProfile.student_id == UUID(student_id))
        diagnosis_count_result = await db.execute(diagnosis_count_stmt)
        diagnosis_count = len(diagnosis_count_result.scalars().all())

        # Build report data
        report_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "report_id": str(profile.id),
            "student": {
                "id": str(student.id),
                "name": f"{student.first_name or ''} {student.full_name or ''}".strip() or "Unknown",
                "age": getattr(student, "age", None),
                "gender": getattr(student, "gender", None),
                "grade": student.current_grade or "N/A",
                "school": student.school.name if student.school else "N/A",
                "school_type": student.school.school_type if student.school else "N/A",
                "home_language": getattr(student, "home_language", None),
                "school_language": getattr(student, "school_language", "English"),
                "diagnosis_count": diagnosis_count,
            },
            "ai_metadata": {
                "analysis_id": str(ai_usage.id) if ai_usage else "N/A",
                "timestamp": ai_usage.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if ai_usage else "N/A",
                "provider": ai_usage.provider if ai_usage else "N/A",
                "model": ai_usage.model if ai_usage else "N/A",
                "prompt": ai_usage.prompt_id if ai_usage else "N/A",
                "input_tokens": f"{ai_usage.input_tokens:,}" if ai_usage else "N/A",
                "output_tokens": f"{ai_usage.output_tokens:,}" if ai_usage else "N/A",
                "total_tokens": f"{(ai_usage.input_tokens + ai_usage.output_tokens):,}" if ai_usage else "N/A",
                "latency_ms": f"{ai_usage.latency_ms:.2f}" if ai_usage else "N/A",
                "latency_seconds": f"{(float(ai_usage.latency_ms) / 1000):.2f}" if ai_usage else "N/A",
                "input_cost": f"{ai_usage.input_cost_usd:.6f}" if ai_usage else "0.000000",
                "output_cost": f"{ai_usage.output_cost_usd:.6f}" if ai_usage else "0.000000",
                "total_cost": f"{ai_usage.total_cost_usd:.6f}" if ai_usage else "0.000000",
                "success": str(ai_usage.success) if ai_usage else "N/A",
            },
            "analysis": {
                "topic": metadata_dict.get("topic", "Mathematics"),
                "readable": metadata_dict.get("readable", True),
                "confidence": metadata_dict.get("confidence", 0),
                "student_approach": metadata_dict.get("student_approach", "Standard approach"),
                "errors": metadata_dict.get("errors", []),
                "patterns": metadata_dict.get("patterns", []),
                "gap_nodes": gap_nodes_data,
                "focus_areas": metadata_dict.get("focus_areas", []),
                "reasoning": metadata_dict.get("reasoning", ""),
            },
            "historical_usage": [
                {
                    "timestamp": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "model": log.model,
                    "prompt": log.prompt_id,
                    "cost": f"{log.total_cost_usd:.6f}",
                    "latency_ms": f"{log.latency_ms:.0f}",
                    "status": "✓ Success" if log.success else "✗ Failed",
                }
                for log in historical_usage_logs
            ],
            "raw_response": json.dumps(metadata_dict, indent=2),
        }

        return templates.TemplateResponse(
            "student_detailed_report.html",
            {
                "request": request,
                "teacher_phone": teacher_phone,
                "student_name": report_data["student"]["name"],
                "report": report_data,
            },
        )

    except Exception as e:
        logger.error(f"Error loading student detailed report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_or_create_demo_teacher(
    db: AsyncSession, phone: str
) -> Teacher:
    """Get or create a demo teacher account."""
    try:
        # Try to find existing
        stmt = select(Teacher).where(Teacher.phone == phone)
        result = await db.execute(stmt)
        teacher = result.scalar_one_or_none()

        if not teacher:
            logger.info(f"Creating new demo teacher for {phone}")
            # Create new demo teacher
            teacher = Teacher(
                phone=phone,
                first_name="Demo",
                last_name="Teacher",
                class_name=None,
                school_id=None,
            )
            db.add(teacher)
            await db.commit()
            await db.refresh(teacher)
            logger.info(f"Demo teacher created successfully: {teacher.id}")

        return teacher
    except Exception as e:
        logger.error(f"Error in get_or_create_demo_teacher: {e}", exc_info=True)
        raise
