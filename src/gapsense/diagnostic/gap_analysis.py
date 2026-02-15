"""
Gap Profile Analysis Service

Generates student gap profiles from completed diagnostic sessions.
Implements root cause analysis and actionable recommendations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.core.models import DiagnosticSession, GapProfile


class GapProfileAnalyzer:
    """Analyzes diagnostic session results and generates gap profiles.

    Implements:
    - Root cause identification
    - Cascade path detection
    - Grade level estimation
    - Actionable recommendations
    """

    def __init__(self, session: DiagnosticSession, db: AsyncSession):
        """Initialize gap profile analyzer.

        Args:
            session: Completed diagnostic session
            db: Database session
        """
        self.session = session
        self.db = db

    async def generate_gap_profile(self) -> GapProfile:
        """Generate comprehensive gap profile from session results.

        Returns:
            GapProfile instance (not yet committed)
        """
        from sqlalchemy import select, update

        from gapsense.core.models import GapProfile, Student

        # Get student
        result = await self.db.execute(select(Student).where(Student.id == self.session.student_id))
        student = result.scalar_one()

        # Deactivate previous gap profiles
        await self.db.execute(
            update(GapProfile)
            .where(GapProfile.student_id == student.id, GapProfile.is_current == True)  # noqa: E712
            .values(is_current=False)
        )

        # Analyze session results
        primary_gap_node = await self._identify_primary_gap()
        estimated_grade = await self._estimate_grade_level()
        grade_gap = self._calculate_grade_gap(student.current_grade, estimated_grade)
        recommended_focus = await self._determine_focus_node()
        overall_confidence = self._calculate_confidence()
        primary_cascade = await self._identify_primary_cascade()

        # Create gap profile
        gap_profile = GapProfile(
            student_id=student.id,
            session_id=self.session.id,
            mastered_nodes=self.session.nodes_mastered or [],
            gap_nodes=self.session.nodes_gap or [],
            uncertain_nodes=[],  # TODO: Track uncertain nodes
            primary_gap_node=primary_gap_node,
            primary_cascade=primary_cascade,
            secondary_gaps=[],  # TODO: Identify secondary gaps
            recommended_focus_node=recommended_focus,
            recommended_activity=None,  # TODO: Generate activity recommendation
            estimated_grade_level=estimated_grade,
            grade_gap=grade_gap,
            overall_confidence=overall_confidence,
            is_current=True,
        )

        return gap_profile

    async def _identify_primary_gap(self) -> UUID | None:
        """Identify the primary (deepest/highest severity) gap node.

        Returns:
            UUID of primary gap node, or None if no gaps found
        """
        if self.session.root_gap_node_id:
            return self.session.root_gap_node_id

        if not self.session.nodes_gap:
            return None

        # Find gap with highest severity
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode

        result = await self.db.execute(
            select(CurriculumNode)
            .where(CurriculumNode.id.in_(self.session.nodes_gap))
            .order_by(CurriculumNode.severity.desc())
        )
        primary_gap = result.scalars().first()

        return primary_gap.id if primary_gap else None

    async def _estimate_grade_level(self) -> str | None:
        """Estimate student's functional grade level based on mastery.

        Returns:
            Estimated grade (e.g., 'B2', 'B3') or None
        """
        if not self.session.nodes_mastered:
            return "B1"  # Default to lowest if nothing mastered

        # Get highest grade among mastered nodes
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode

        result = await self.db.execute(
            select(CurriculumNode.grade)
            .where(CurriculumNode.id.in_(self.session.nodes_mastered))
            .distinct()
        )
        mastered_grades = result.scalars().all()

        if not mastered_grades:
            return "B1"

        # Return highest mastered grade
        # Assumes grades are B1-B9 format
        sorted_grades = sorted(mastered_grades, key=lambda g: int(g[1:]))
        return sorted_grades[-1]

    def _calculate_grade_gap(self, current_grade: str, estimated_grade: str | None) -> int | None:
        """Calculate gap between current and estimated grade level.

        Args:
            current_grade: Enrolled grade (e.g., 'B5')
            estimated_grade: Functional grade (e.g., 'B3')

        Returns:
            Number of grades behind (positive int) or None
        """
        if not estimated_grade:
            return None

        try:
            current = int(current_grade[1:])
            estimated = int(estimated_grade[1:])
            gap = current - estimated
            return max(0, gap)  # Never negative
        except (ValueError, IndexError):
            return None

    async def _identify_primary_cascade(self) -> str | None:
        """Identify the primary cascade path containing the root gap.

        Returns:
            Cascade path name if identified, None otherwise
        """
        if not self.session.root_gap_node_id:
            return None

        from sqlalchemy import select

        from gapsense.core.models import CascadePath

        # Get all cascade paths
        result = await self.db.execute(select(CascadePath))
        all_cascades = result.scalars().all()

        # Find cascade containing the root gap node
        for cascade in all_cascades:
            if self.session.root_gap_node_id in cascade.node_sequence:
                return cascade.name

        return None

    async def _determine_focus_node(self) -> UUID | None:
        """Determine which node student should work on first.

        Priority:
        1. Primary gap node (if identified)
        2. Highest severity gap
        3. None (if no gaps)

        Returns:
            UUID of focus node or None
        """
        # Use primary gap as focus
        return await self._identify_primary_gap()

    def _calculate_confidence(self) -> float:
        """Calculate overall confidence in gap profile.

        Based on:
        - Number of questions asked
        - Consistency of responses
        - Coverage of screening nodes

        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.5  # Base confidence

        # Increase confidence with more questions
        if self.session.total_questions >= 12:
            confidence += 0.2
        elif self.session.total_questions >= 8:
            confidence += 0.1

        # Increase if root gap identified
        if self.session.root_gap_node_id and self.session.root_gap_confidence:
            confidence += 0.2

        # Cap at 0.95 (never 100% certain)
        return min(confidence, 0.95)

    async def generate_ai_root_cause_analysis(self) -> dict[str, str | list[str]] | None:
        """Use AI (DIAG-003) to generate deep root cause analysis.

        Returns:
            Dict with:
                - root_cause_explanation: str
                - primary_cascade: str
                - mastered_node_codes: list[str]
                - gap_node_codes: list[str]
                - uncertain_node_codes: list[str]
                - parent_message: str
                - recommended_activities: list[str]
            Or None if AI analysis fails
        """
        try:
            import json

            from anthropic import Anthropic
            from sqlalchemy import select

            from gapsense.ai import get_prompt_library
            from gapsense.config import settings
            from gapsense.core.models import Parent, Student

            # Get DIAG-003 prompt
            lib = get_prompt_library()
            prompt = lib.get_prompt("DIAG-003")

            # Get student
            result = await self.db.execute(
                select(Student).where(Student.id == self.session.student_id)
            )
            student = result.scalar_one()

            # Get parent for language preference
            parent_result = await self.db.execute(
                select(Parent).where(Parent.id == student.primary_parent_id)
            )
            parent = parent_result.scalar_one_or_none()

            # Build session Q&A history
            session_history = await self._build_session_qa_history()

            # Build relevant graph nodes
            relevant_nodes = await self._build_relevant_graph_nodes()

            # Calculate session duration
            session_duration_minutes = 0
            if self.session.completed_at and self.session.created_at:
                duration = self.session.completed_at - self.session.created_at
                session_duration_minutes = int(duration.total_seconds() / 60)

            # Build context for AI
            context = {
                "student_first_name": student.first_name or "Student",
                "current_grade": student.current_grade,
                "age": str(student.age) if student.age else "unknown",
                "home_language": student.home_language or "English",
                "parent_preferred_language": parent.preferred_language if parent else "English",
                "session_qa_history_json": json.dumps(session_history, indent=2),
                "relevant_graph_nodes_json": json.dumps(relevant_nodes, indent=2),
                "total_questions": str(self.session.total_questions),
                "session_duration_minutes": str(session_duration_minutes),
            }

            # Format user message from template
            user_message = prompt["user_template"]
            for key, value in context.items():
                user_message = user_message.replace(f"{{{{{key}}}}}", str(value))

            # Call Claude API
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            response = client.messages.create(
                model=prompt["model"],
                max_tokens=prompt["max_tokens"],
                temperature=prompt["temperature"],
                system=prompt["system_prompt"],
                messages=[{"role": "user", "content": user_message}],
            )

            # Parse response
            content_block = response.content[0]
            if not hasattr(content_block, "text"):
                return None

            response_data = json.loads(content_block.text)

            return {
                "root_cause_explanation": response_data.get("root_cause_explanation", ""),
                "primary_cascade": response_data.get("primary_cascade", ""),
                "mastered_node_codes": response_data.get("mastered_nodes", []),
                "gap_node_codes": response_data.get("gap_nodes", []),
                "uncertain_node_codes": response_data.get("uncertain_nodes", []),
                "parent_message": response_data.get("parent_message", ""),
                "recommended_activities": response_data.get("recommended_activities", []),
            }

        except Exception:
            # Return None on error, caller should fallback to rule-based analysis
            return None

    async def _build_session_qa_history(self) -> list[dict[str, str | bool]]:
        """Build complete Q&A history for the session.

        Returns:
            List of dicts with question, answer, correctness, node_code
        """
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode, DiagnosticQuestion

        # Get all answered questions for this session
        questions_result = await self.db.execute(
            select(DiagnosticQuestion)
            .where(
                DiagnosticQuestion.session_id == self.session.id,
                DiagnosticQuestion.student_response.isnot(None),
            )
            .order_by(DiagnosticQuestion.question_order)
        )
        questions = questions_result.scalars().all()

        history = []
        for question in questions:
            # Get node code
            node_result = await self.db.execute(
                select(CurriculumNode).where(CurriculumNode.id == question.node_id)
            )
            node = node_result.scalar_one_or_none()

            if node:
                history.append(
                    {
                        "node_code": node.code,
                        "question": question.question_text,
                        "expected_answer": question.expected_answer or "N/A",
                        "student_response": question.student_response or "",
                        "is_correct": question.is_correct or False,
                    }
                )

        return history

    async def _build_relevant_graph_nodes(self) -> list[dict[str, str | int]]:
        """Build prerequisite graph nodes relevant to this session.

        Returns:
            List of node dicts with code, title, grade, severity
        """
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode

        # Get all nodes that were tested or identified as gaps
        all_node_ids = set()
        if self.session.nodes_tested:
            all_node_ids.update(self.session.nodes_tested)
        if self.session.nodes_gap:
            all_node_ids.update(self.session.nodes_gap)
        if self.session.nodes_mastered:
            all_node_ids.update(self.session.nodes_mastered)

        if not all_node_ids:
            return []

        result = await self.db.execute(
            select(CurriculumNode).where(CurriculumNode.id.in_(all_node_ids))
        )
        nodes = result.scalars().all()

        return [
            {
                "code": node.code,
                "title": node.title,
                "grade": node.grade,
                "severity": node.severity,
            }
            for node in nodes
        ]

    async def generate_recommendations(self, gap_profile: GapProfile) -> dict[str, str]:
        """Generate actionable recommendations for student/parent.

        Args:
            gap_profile: Gap profile to generate recommendations for

        Returns:
            Dict with recommendation keys and values
        """
        # Try AI-powered recommendations first
        ai_analysis = await self.generate_ai_root_cause_analysis()

        if ai_analysis and ai_analysis.get("recommended_activities"):
            activities = ai_analysis["recommended_activities"]
            activities_str = (
                ", ".join(activities) if isinstance(activities, list) else str(activities)
            )
            parent_msg = ai_analysis.get("parent_message", "Practice foundational skills")
            parent_msg_str = str(parent_msg) if parent_msg else "Practice foundational skills"
            root_cause = ai_analysis.get("root_cause_explanation", "")
            root_cause_str = str(root_cause) if root_cause else ""

            return {
                "next_steps": parent_msg_str,
                "recommended_activities": activities_str,
                "root_cause": root_cause_str,
            }

        # Fallback to rule-based recommendations
        return {
            "next_steps": "Practice foundational skills",
            "estimated_time": "2-3 weeks of daily practice",
            "materials_needed": "Paper, pencil, everyday objects",
        }
