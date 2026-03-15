"""
Parent Activity Delivery with TTS Voice Notes (Req 10)

Generates personalized daily activities, validates through GUARD-001,
converts to TTS voice notes, and delivers via WhatsApp.
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
    from gapsense.core.models.diagnostics import GapProfile
    from gapsense.services.guard_service import GuardService
    from gapsense.services.worker_service import WorkerService

from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


@dataclass
class ActivityDeliveryResult:
    """Result of activity delivery attempt."""

    success: bool
    activity_text: str | None = None
    tts_enqueued: bool = False
    text_sent: bool = False
    guard_passed: bool = False
    error: str | None = None


class ParentActivityDelivery:
    """Generates and delivers personalized parent activities with TTS."""

    def __init__(
        self,
        *,
        db: AsyncSession,
        ai_client: AsyncAIClient,
        prompt_service: PromptService,
        guard_service: GuardService,
        worker_service: WorkerService,
    ) -> None:
        self.db = db
        self._ai_client = ai_client
        self._prompt_service = prompt_service
        self._guard_service = guard_service
        self._worker_service = worker_service

    async def deliver_activity(
        self,
        *,
        parent: Parent,
        student: Student,
        gap_profile: GapProfile,
        country: str = "GH",
        language: str = "en",
    ) -> ActivityDeliveryResult:
        """Generate and deliver a personalized activity to a parent.

        1. Generate activity using PARENT-001 + ACT-001 prompts
        2. Validate through GUARD-001
        3. Enqueue TTS generation
        4. Send text version
        """
        from gapsense.services.worker_service import WorkerTask

        try:
            # Step 1: Generate activity using PARENT-001
            parent_prompt = self._prompt_service.render_prompt(
                "PARENT-001",
                country=country,
                language=language,
                extra_context={
                    "student_name": student.full_name or "your child",
                    "gap_summary": str(gap_profile.gap_nodes[:3]),
                },
            )

            parent_response = await self._ai_client.generate(
                prompt_id="PARENT-001",
                system=parent_prompt.system_prompt,
                messages=[{"role": "user", "content": "Generate today's activity."}],
                model=parent_prompt.model,
                temperature=parent_prompt.temperature,
                max_tokens=parent_prompt.max_tokens,
            )

            if parent_response is None:
                return ActivityDeliveryResult(success=False, error="AI unavailable")

            # Step 2: Generate specific 3-minute activity using ACT-001
            act_prompt = self._prompt_service.render_prompt(
                "ACT-001",
                country=country,
                language=language,
            )

            act_response = await self._ai_client.generate(
                prompt_id="ACT-001",
                system=act_prompt.system_prompt,
                messages=[
                    {"role": "user", "content": parent_response.text},
                ],
                model=act_prompt.model,
                temperature=act_prompt.temperature,
                max_tokens=act_prompt.max_tokens,
            )

            activity_text = act_response.text if act_response else parent_response.text

            # Step 3: Validate through GUARD-001
            guard_result = await self._guard_service.check(
                activity_text,
                student_context={"student_id": str(student.id)},
                country=country,
                language=language,
            )

            if not guard_result.passed:
                logger.warning(
                    "activity_blocked_by_guard",
                    violations=guard_result.violations,
                )
                return ActivityDeliveryResult(
                    success=False,
                    activity_text=activity_text,
                    guard_passed=False,
                    error=f"Guard violations: {guard_result.violations}",
                )

            # Step 4: Enqueue TTS generation
            tts_task = WorkerTask(
                task_type="tts_generate",
                payload={
                    "text": activity_text,
                    "language": language,
                    "country": country,
                    "student_id": str(student.id),
                    "parent_phone": parent.phone,
                },
            )
            await self._worker_service.enqueue(tts_task)

            # Step 5: Send text version alongside
            client = WhatsAppClient.from_settings()
            try:
                await client.send_text_message(
                    to=parent.phone,
                    text=activity_text,
                )
                text_sent = True
            except Exception as e:
                logger.warning(f"Failed to send text activity to {parent.phone}: {e}")
                text_sent = False

            return ActivityDeliveryResult(
                success=True,
                activity_text=activity_text,
                tts_enqueued=True,
                text_sent=text_sent,
                guard_passed=True,
            )

        except Exception as e:
            logger.error(f"Activity delivery failed: {e}", exc_info=True)
            return ActivityDeliveryResult(success=False, error=str(e))

    @staticmethod
    def get_delivery_time(country: str) -> str:
        """Get optimal delivery time for a country (default 6:30 PM local).

        Returns time string in HH:MM format.
        """
        # Country-specific delivery times
        delivery_times = {
            "GH": "18:30",  # 6:30 PM GMT
            "UG": "18:30",  # 6:30 PM EAT
            "KE": "18:30",  # 6:30 PM EAT
            "NG": "18:30",  # 6:30 PM WAT
        }
        return delivery_times.get(country, "18:30")
