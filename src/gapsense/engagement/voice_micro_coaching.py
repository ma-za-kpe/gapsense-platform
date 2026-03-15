"""
Voice Micro-Coaching for Parents (Req 12)

Handles parent voice messages: transcribes, analyzes with ANALYSIS-002,
generates coaching feedback, validates through GUARD-001, and delivers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.core.models import Parent, Student
    from gapsense.services.guard_service import GuardService
    from gapsense.services.media_service import MediaService
    from gapsense.services.worker_service import WorkerService

from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


@dataclass
class CoachingResult:
    """Result of voice micro-coaching processing."""

    success: bool
    transcript: str | None = None
    coaching_text: str | None = None
    message_sent: bool = False
    error: str | None = None


class VoiceMicroCoaching:
    """Processes parent voice messages for coaching feedback."""

    def __init__(
        self,
        *,
        db: AsyncSession,
        ai_client: AsyncAIClient,
        prompt_service: PromptService,
        guard_service: GuardService,
        media_service: MediaService,
        worker_service: WorkerService,
    ) -> None:
        self.db = db
        self._ai_client = ai_client
        self._prompt_service = prompt_service
        self._guard_service = guard_service
        self._media_service = media_service
        self._worker_service = worker_service

    async def handle_voice_message(
        self,
        *,
        parent: Parent,
        student: Student,
        audio_bytes: bytes,
        filename: str,
        content_type: str = "audio/ogg",
        country: str = "GH",
        language: str = "en",
    ) -> CoachingResult:
        """Process a parent's voice message.

        1. Upload audio to S3
        2. Enqueue voice_transcribe task
        3. Send acknowledgment
        """
        from gapsense.services.worker_service import WorkerTask

        try:
            # Upload audio to S3
            s3_key = await self._media_service.upload(
                audio_bytes,
                country=country,
                student_id=str(student.id),
                media_type="audio",
                filename=filename,
                content_type=content_type,
            )

            # Enqueue transcription task
            task = WorkerTask(
                task_type="voice_transcribe",
                payload={
                    "s3_key": s3_key,
                    "parent_id": str(parent.id),
                    "student_id": str(student.id),
                    "country": country,
                    "language": language,
                },
            )
            await self._worker_service.enqueue(task)

            # Send acknowledgment
            client = WhatsAppClient.from_settings()
            try:
                await client.send_text_message(
                    to=parent.phone,
                    text="🎤 Got your voice message! I'm listening and will respond shortly.",
                )
            except Exception as e:
                logger.warning(f"Failed to send ack to {parent.phone}: {e}")

            return CoachingResult(success=True)

        except Exception as e:
            logger.error(f"Voice coaching failed: {e}", exc_info=True)
            return CoachingResult(success=False, error=str(e))

    async def process_transcript(
        self,
        *,
        parent_id: str,
        student_id: str,
        transcript: str,
        country: str = "GH",
        language: str = "en",
    ) -> CoachingResult:
        """Process completed transcription and generate coaching feedback.

        Called by WorkerService after voice_transcribe task completes.

        1. Send transcript to AI with ANALYSIS-002 for coaching analysis
        2. Validate through GUARD-001
        3. Send coaching feedback to parent
        4. Update ParentInteraction record
        """
        from uuid import UUID

        try:
            # Analyze with ANALYSIS-002
            prompt = self._prompt_service.render_prompt(
                "ANALYSIS-002",
                country=country,
                language=language,
            )

            response = await self._ai_client.generate(
                prompt_id="ANALYSIS-002",
                system=prompt.system_prompt,
                messages=[{"role": "user", "content": transcript}],
                model=prompt.model,
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
                json_mode=True,
            )

            if response is None:
                return CoachingResult(
                    success=False,
                    transcript=transcript,
                    error="AI unavailable",
                )

            # Parse coaching response
            coaching_data = response.json_parsed or {}
            engagement = coaching_data.get("engagement_assessment", "")
            feedback = coaching_data.get("coaching_feedback", response.text)
            follow_up = coaching_data.get("follow_up_activity", "")

            coaching_text = feedback
            if follow_up:
                coaching_text += f"\n\n📝 Try this next: {follow_up}"

            # Validate through GUARD-001
            guard_result = await self._guard_service.check(
                coaching_text,
                student_context={"student_id": student_id},
                country=country,
                language=language,
            )

            if not guard_result.passed:
                logger.warning(
                    "coaching_blocked_by_guard",
                    violations=guard_result.violations,
                )
                return CoachingResult(
                    success=False,
                    transcript=transcript,
                    coaching_text=coaching_text,
                    error=f"Guard violations: {guard_result.violations}",
                )

            # Send to parent
            from sqlalchemy import select

            from gapsense.core.models.students import Parent as ParentModel

            result = await self.db.execute(
                select(ParentModel).where(ParentModel.id == UUID(parent_id))
            )
            parent = result.scalar_one_or_none()

            if parent:
                client = WhatsAppClient.from_settings()
                try:
                    await client.send_text_message(
                        to=parent.phone,
                        text=coaching_text,
                    )
                    message_sent = True
                except Exception as e:
                    logger.warning(f"Failed to send coaching to {parent.phone}: {e}")
                    message_sent = False
            else:
                message_sent = False

            # Update ParentInteraction record
            await self._update_interaction(
                parent_id=parent_id,
                student_id=student_id,
                transcript=transcript,
                sentiment=coaching_data.get("sentiment_score"),
                coaching_response=coaching_text,
            )

            return CoachingResult(
                success=True,
                transcript=transcript,
                coaching_text=coaching_text,
                message_sent=message_sent,
            )

        except Exception as e:
            logger.error(f"Coaching processing failed: {e}", exc_info=True)
            return CoachingResult(success=False, transcript=transcript, error=str(e))

    async def _update_interaction(
        self,
        *,
        parent_id: str,
        student_id: str,
        transcript: str,
        sentiment: float | None,
        coaching_response: str,
    ) -> None:
        """Update ParentInteraction record with transcript and coaching data."""
        try:
            from sqlalchemy import select

            from gapsense.core.models.engagement import ParentInteraction

            result = await self.db.execute(
                select(ParentInteraction)
                .where(ParentInteraction.parent_id == parent_id)
                .order_by(ParentInteraction.created_at.desc())
                .limit(1)
            )
            interaction = result.scalar_one_or_none()

            if interaction:
                interaction.voice_transcript = transcript
                if sentiment is not None:
                    interaction.sentiment_score = sentiment
                interaction.coaching_response = coaching_response
                await self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to update interaction: {e}")
