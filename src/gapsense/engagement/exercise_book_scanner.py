"""
Exercise Book Scanner Integration (Req 9)

Handles teacher image messages: uploads to S3, enqueues image_analyze task,
processes results into GapProfiles, and sends teacher summaries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.core.models import Student, Teacher
    from gapsense.services.guard_service import GuardService
    from gapsense.services.media_service import MediaService
    from gapsense.services.worker_service import WorkerService

from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


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

            # Send acknowledgment
            client = WhatsAppClient.from_settings()
            try:
                await client.send_text_message(
                    to=teacher.phone,
                    text="📸 Analyzing the exercise book page. I'll send you the results shortly.",
                )
            except Exception as e:
                logger.warning(f"Failed to send ack to {teacher.phone}: {e}")

            return ScanResult(success=True, s3_key=s3_key, task_enqueued=True, message_sent=True)

        except Exception as e:
            logger.error(f"Exercise book scan failed: {e}", exc_info=True)
            return ScanResult(success=False, error=str(e))

    async def process_analysis_result(
        self,
        *,
        student_id: str,
        teacher_phone: str,
        analysis: dict[str, Any],
        country: str = "GH",
        language: str = "en",
    ) -> None:
        """Process completed image analysis and update GapProfile.

        Called by WorkerService after image_analyze task completes.
        """
        from uuid import UUID

        from sqlalchemy import select

        from gapsense.core.models.diagnostics import GapProfile

        # Check for unreadable image
        if analysis.get("unreadable"):
            client = WhatsAppClient.from_settings()
            await client.send_text_message(
                to=teacher_phone,
                text="📷 The image was too blurry to analyze. Could you retake the photo with better lighting?",
            )
            return

        # Create/update GapProfile with source="exercise_book"
        gap_nodes = [UUID(code) for code in analysis.get("gap_node_ids", []) if code]
        focus_areas = analysis.get("focus_areas", [])

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
        else:
            profile = GapProfile(
                student_id=UUID(student_id),
                session_id=None,
                source="exercise_book",
                gap_nodes=gap_nodes,
                mastered_nodes=[],
                uncertain_nodes=[],
            )
            self.db.add(profile)

        await self.db.commit()

        # Send summary to teacher via GuardService
        errors = analysis.get("errors", [])
        patterns = analysis.get("patterns", [])
        summary = self._build_teacher_summary(errors, patterns, focus_areas)

        guard_result = await self._guard_service.check(
            summary,
            student_context={"student_id": student_id},
            country=country,
            language=language,
        )

        if guard_result.passed:
            client = WhatsAppClient.from_settings()
            await client.send_text_message(to=teacher_phone, text=summary)

    @staticmethod
    def _build_teacher_summary(
        errors: list[dict], patterns: list[str], focus_areas: list[str]
    ) -> str:
        """Build a human-readable summary for the teacher."""
        lines = ["📊 Exercise Book Analysis Complete\n"]

        if errors:
            lines.append(f"Found {len(errors)} error(s):")
            for err in errors[:5]:
                desc = err.get("description", "Unknown error")
                lines.append(f"  • {desc}")

        if patterns:
            lines.append(f"\nPatterns identified: {', '.join(patterns[:3])}")

        if focus_areas:
            lines.append(f"\nRecommended focus: {', '.join(focus_areas[:3])}")

        return "\n".join(lines)
