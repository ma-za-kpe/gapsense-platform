"""
Exercise Book Scanner Integration (Req 9)

Handles teacher image messages: uploads to S3, enqueues image_analyze task,
processes results into GapProfiles, and sends teacher summaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.core.models import Student, Teacher
    from gapsense.services.guard_service import GuardService
    from gapsense.services.media_service import MediaService
    from gapsense.services.worker_service import WorkerService

from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = structlog.get_logger(__name__)


@dataclass
class ScanResult:
    """Result of exercise book scan processing."""

    success: bool
    s3_key: str | None = None
    task_enqueued: bool = False
    message_sent: bool = False
    error: str | None = None


class ExerciseBookScanner:
    """Handles exercise book photo analysis flow for teachers."""

    def __init__(
        self,
        *,
        db: AsyncSession,
        media_service: MediaService,
        worker_service: WorkerService,
        guard_service: GuardService,
        ai_client: AsyncAIClient,
        prompt_service: PromptService,
    ) -> None:
        self.db = db
        self._media_service = media_service
        self._worker_service = worker_service
        self._guard_service = guard_service
        self._ai_client = ai_client
        self._prompt_service = prompt_service

    @staticmethod
    def _is_demo_mode(teacher_phone: str) -> bool:
        """Check if this is a demo mode teacher (bypasses WhatsApp/Twilio).

        Demo phones use patterns:
        - +2335000* (test scripts with double-zero)
        - +23350 followed by test patterns like "1234567"
        - Contains obvious test patterns

        These won't conflict with real Vodafone numbers (+233 50X... where X is 1-9).
        """
        # Check for test phone patterns
        if teacher_phone.startswith("+2335000"):  # Double-zero test phones
            return True

        # Check for obvious test patterns (with or without leading zero)
        test_patterns = ["1234567", "01234567", "1111111", "2222222", "0000000", "9999999"]
        return any(pattern in teacher_phone for pattern in test_patterns)

    async def handle_image_message(
        self,
        *,
        teacher: Teacher,
        student: Student,
        image_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        country: str = "GH",
    ) -> ScanResult:
        """Process an exercise book image from a teacher.

        1. Upload image to S3 via MediaService
        2. Enqueue image_analyze task to WorkerService
        3. Send "analyzing" acknowledgment to teacher
        """
        from gapsense.services.worker_service import WorkerTask

        try:
            # Upload image to S3
            s3_key = await self._media_service.upload(
                image_bytes,
                country=country,
                student_id=str(student.id),
                media_type="image",
                filename=filename,
                content_type=content_type,
            )

            # Enqueue analysis task
            task = WorkerTask(
                task_type="image_analyze",
                payload={
                    "s3_key": s3_key,
                    "student_id": str(student.id),
                    "teacher_phone": teacher.phone,
                    "country": country,
                },
            )
            await self._worker_service.enqueue(task)

            # Send acknowledgment (skip in demo mode - UI polls for completion)
            if not self._is_demo_mode(teacher.phone):
                client = WhatsAppClient.from_settings()
                try:
                    await client.send_text_message(
                        to=teacher.phone,
                        text="📸 Analyzing the exercise book page. I'll send you the results shortly.",
                    )
                except Exception as e:
                    logger.warning("failed_to_send_ack", teacher_phone=teacher.phone, error=str(e))
            else:
                logger.info("demo_mode_skip_ack", teacher_phone=teacher.phone)

            return ScanResult(success=True, s3_key=s3_key, task_enqueued=True, message_sent=True)

        except Exception as e:
            logger.error("exercise_book_scan_failed", error=str(e), exc_info=True)
            return ScanResult(success=False, error=str(e))

    async def process_analysis_result(
        self,
        *,
        student_id: str,
        teacher_phone: str,
        analysis: dict[str, Any],
        country: str = "GH",  # noqa: ARG002 - Part of API contract
        language: str = "en",  # noqa: ARG002 - Part of API contract
    ) -> None:
        """Process completed image analysis and update GapProfile.

        Called by WorkerService after image_analyze task completes.
        """
        from uuid import UUID

        from sqlalchemy import select

        from gapsense.core.models import Student
        from gapsense.core.models.diagnostics import GapProfile

        logger.info(
            "process_analysis_result_start",
            student_id=student_id,
            teacher_phone=teacher_phone,
            gap_count=len(analysis.get("gap_node_ids", [])),
        )

        # Get student name for personalized message
        student_result = await self.db.execute(
            select(Student).where(Student.id == UUID(student_id))
        )
        student = student_result.scalar_one_or_none()
        student_name = student.first_name if student and student.first_name else "Student"

        # Check for unreadable image
        if analysis.get("unreadable"):
            logger.info(
                "unreadable_image_detected",
                student_id=student_id,
                teacher_phone=teacher_phone,
            )
            if not self._is_demo_mode(teacher_phone):
                client = WhatsAppClient.from_settings()
                await client.send_text_message(
                    to=teacher_phone,
                    text=f"📷 {student_name}'s exercise book was too blurry to analyze. Could you retake the photo with better lighting?",
                )
            else:
                logger.info("demo_mode_skip_unreadable_msg", teacher_phone=teacher_phone)
            return

        # Create/update GapProfile with source="exercise_book"
        # Convert curriculum codes to node UUIDs
        from gapsense.core.models import CurriculumNode

        gap_codes = analysis.get("gap_node_ids", [])
        gap_nodes = []
        if gap_codes:
            nodes_result = await self.db.execute(
                select(CurriculumNode.id).where(CurriculumNode.code.in_(gap_codes))
            )
            gap_nodes = [row[0] for row in nodes_result.fetchall()]

        focus_areas = analysis.get("focus_areas", [])

        # Store analysis metadata for dashboard
        metadata = {
            "errors": analysis.get("errors", []),
            "patterns": analysis.get("patterns", []),
            "focus_areas": focus_areas,
            "image_quality": analysis.get("image_quality", "unknown"),
            "confidence": analysis.get("confidence", 0.0),
        }

        result = await self.db.execute(
            select(GapProfile).where(
                GapProfile.student_id == UUID(student_id),
                GapProfile.is_current == True,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.gap_nodes = list(set(existing.gap_nodes + gap_nodes))
            existing.source = "exercise_book"
            existing.analysis_metadata = metadata
        else:
            profile = GapProfile(
                student_id=UUID(student_id),
                session_id=None,
                source="exercise_book",
                gap_nodes=gap_nodes,
                mastered_nodes=[],
                uncertain_nodes=[],
                analysis_metadata=metadata,
            )
            self.db.add(profile)

        await self.db.commit()

        logger.info(
            "gap_profile_saved",
            student_id=student_id,
            student_name=student_name,
            gap_nodes_count=len(gap_nodes),
        )

        # Send WhatsApp message with link to comprehensive dashboard
        from gapsense.config import settings

        # Build dashboard URL
        dashboard_url = f"{settings.APP_URL}/demo/reports/{teacher_phone}"

        message = (
            f"✅ *{student_name}'s Exercise Book Analysis Complete*\n\n"
            f"📊 View comprehensive report:\n"
            f"{dashboard_url}\n\n"
            f"Your dashboard shows:\n"
            f"• Detailed gap analysis\n"
            f"• All students overview\n"
            f"• Focus areas & patterns\n"
            f"• Priority recommendations"
        )

        # Send via WhatsApp (skip in demo mode - UI polls for gap profile)
        if not self._is_demo_mode(teacher_phone):
            client = WhatsAppClient.from_settings()
            await client.send_text_message(to=teacher_phone, text=message, preview_url=True)
            logger.info(
                "analysis_complete_message_sent",
                teacher_phone=teacher_phone,
                student_name=student_name,
                dashboard_url=dashboard_url,
            )
        else:
            logger.info(
                "demo_mode_skip_whatsapp",
                teacher_phone=teacher_phone,
                student_name=student_name,
                dashboard_url=dashboard_url,
                message="Demo mode: Gap profile saved, UI will detect via polling",
            )

    @staticmethod
    def _build_teacher_summary(
        student_name: str, errors: list[dict], patterns: list[str], focus_areas: list[str]
    ) -> str:
        """Build a human-readable summary for the teacher."""
        lines = [f"✅ {student_name}'s Exercise Book Analysis Complete\n"]

        if errors:
            lines.append(f"Found {len(errors)} error(s):")
            for err in errors[:5]:
                desc = err.get("description", "Unknown error")
                lines.append(f"  • {desc}")

        if patterns:
            lines.append(f"\nPatterns identified: {', '.join(patterns[:3])}")

        if focus_areas:
            lines.append(f"\n💡 Recommended focus: {', '.join(focus_areas[:3])}")

        lines.append(f"\n📊 For full gap report, type: /STUDENT {student_name}")

        return "\n".join(lines)
