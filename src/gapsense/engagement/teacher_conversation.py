"""
Teacher Conversation Partner (Req 11)

AI-powered pedagogical conversation for teachers via WhatsApp.
Uses TEACHER-001/002/003 prompts with class aggregate gap data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.core.models import Teacher

from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


@dataclass
class ConversationResult:
    """Result of teacher conversation turn."""

    success: bool
    response_text: str | None = None
    message_sent: bool = False
    error: str | None = None


@dataclass
class ConversationHistory:
    """Maintains multi-turn conversation context for a teacher."""

    teacher_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    max_turns: int = 20

    def add_turn(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        # Keep only last N turns
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2) :]


class TeacherConversationPartner:
    """AI-powered teacher conversation with pedagogical guidance."""

    def __init__(
        self,
        *,
        db: AsyncSession,
        ai_client: AsyncAIClient,
        prompt_service: PromptService,
    ) -> None:
        self.db = db
        self._ai_client = ai_client
        self._prompt_service = prompt_service
        self._histories: dict[str, ConversationHistory] = {}

    async def handle_teacher_message(
        self,
        *,
        teacher: Teacher,
        message: str,
        country: str = "GH",
        language: str = "en",
    ) -> ConversationResult:
        """Process a teacher's text message and generate pedagogical response.

        1. Analyze question with TEACHER-001 + class gap data
        2. Generate response with TEACHER-002
        3. Format for WhatsApp with TEACHER-003
        """
        try:
            teacher_id: str = str(teacher.id)
            history = self._get_or_create_history(teacher_id)
            history.add_turn("user", message)

            # Gather class gap data
            gap_context = await self._get_class_gap_context(teacher)

            # Step 1: Analyze with TEACHER-001
            t1_prompt = self._prompt_service.render_prompt(
                "TEACHER-001",
                country=country,
                language=language,
                extra_context={"class_gap_data": gap_context},
            )

            analysis = await self._ai_client.generate(
                prompt_id="TEACHER-001",
                system=t1_prompt.system_prompt,
                messages=history.messages,
                model=t1_prompt.model,
                temperature=t1_prompt.temperature,
                max_tokens=t1_prompt.max_tokens,
            )

            if analysis is None:
                return ConversationResult(success=False, error="AI unavailable for analysis")

            # Step 2: Generate pedagogical response with TEACHER-002
            t2_prompt = self._prompt_service.render_prompt(
                "TEACHER-002",
                country=country,
                language=language,
            )

            response = await self._ai_client.generate(
                prompt_id="TEACHER-002",
                system=t2_prompt.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Analysis: {analysis.text}\n\nTeacher question: {message}",
                    }
                ],
                model=t2_prompt.model,
                temperature=t2_prompt.temperature,
                max_tokens=t2_prompt.max_tokens,
            )

            if response is None:
                return ConversationResult(
                    success=False, error="AI unavailable for response generation"
                )

            # Step 3: Format for WhatsApp with TEACHER-003
            t3_prompt = self._prompt_service.render_prompt(
                "TEACHER-003",
                country=country,
                language=language,
            )

            formatted = await self._ai_client.generate(
                prompt_id="TEACHER-003",
                system=t3_prompt.system_prompt,
                messages=[{"role": "user", "content": response.text}],
                model=t3_prompt.model,
                temperature=t3_prompt.temperature,
                max_tokens=t3_prompt.max_tokens,
            )

            final_text = formatted.text if formatted else response.text
            history.add_turn("assistant", final_text)

            # Send via WhatsApp
            client = WhatsAppClient.from_settings()
            try:
                await client.send_text_message(to=teacher.phone, text=final_text)
                return ConversationResult(success=True, response_text=final_text, message_sent=True)
            except Exception as e:
                logger.warning(f"Failed to send to {teacher.phone}: {e}")
                return ConversationResult(
                    success=True, response_text=final_text, message_sent=False
                )

        except Exception as e:
            logger.error(f"Teacher conversation failed: {e}", exc_info=True)
            return ConversationResult(success=False, error=str(e))

    async def _get_class_gap_context(self, teacher: Teacher) -> str:
        """Aggregate GapProfile data across teacher's class students."""
        from sqlalchemy import select

        from gapsense.core.models.diagnostics import GapProfile
        from gapsense.core.models.students import Student

        try:
            result = await self.db.execute(
                select(GapProfile)
                .join(Student, GapProfile.student_id == Student.id)
                .where(
                    Student.teacher_id == teacher.id,
                    GapProfile.is_current == True,  # noqa: E712
                )
            )
            profiles = result.scalars().all()

            if not profiles:
                return "No gap data available for this class yet."

            # Aggregate gap nodes across all students
            all_gaps: dict[str, int] = {}
            for p in profiles:
                for gap_id in p.gap_nodes or []:
                    key = str(gap_id)
                    all_gaps[key] = all_gaps.get(key, 0) + 1

            total_students = len(profiles)
            top_gaps = sorted(all_gaps.items(), key=lambda x: x[1], reverse=True)[:5]

            lines = [f"Class: {total_students} students with gap profiles"]
            for gap_id_str, count in top_gaps:
                pct = round(count / total_students * 100)
                lines.append(f"  Gap {gap_id_str}: {count}/{total_students} ({pct}%)")

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Failed to aggregate class gaps: {e}")
            return "Gap data unavailable."

    def _get_or_create_history(self, teacher_id: str) -> ConversationHistory:
        if teacher_id not in self._histories:
            self._histories[teacher_id] = ConversationHistory(teacher_id=teacher_id)
        return self._histories[teacher_id]
