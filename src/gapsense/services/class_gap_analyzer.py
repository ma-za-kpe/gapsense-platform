"""
Class Gap Analyzer Service

Aggregates gap data across students to provide teacher insights:
- Class-wide gap overview
- Common gap identification
- Individual student reports
- Progress tracking
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select

from gapsense.core.models import CurriculumNode, GapProfile, Student


@dataclass
class ClassOverview:
    """Overview of class gap status."""

    total_students: int
    scanned_students: int
    last_scan_date: datetime | None
    common_gaps: list[GapSummary]
    improvement_percentage: int | None


@dataclass
class GapSummary:
    """Summary of a gap found across students."""

    node_code: str
    node_title: str
    student_count: int
    severity: int


@dataclass
class StudentReport:
    """Individual student gap report."""

    student_name: str
    scan_date: datetime | None
    primary_gap: str | None
    gap_list: list[str]
    recommended_actions: str | None
    estimated_time: str | None


class ClassGapAnalyzer:
    """Analyzes gap data across a teacher's class."""

    def __init__(self, db: AsyncSession):
        """Initialize analyzer.

        Args:
            db: Database session
        """
        self.db = db

    async def get_class_overview(self, teacher_id: UUID) -> ClassOverview:
        """Get class-wide gap overview.

        Args:
            teacher_id: Teacher's UUID

        Returns:
            ClassOverview with aggregated data
        """
        # Get all students for this teacher
        students_result = await self.db.execute(
            select(Student).where(
                Student.teacher_id == teacher_id,
            )
        )
        students = students_result.scalars().all()
        total_students = len(students)

        if total_students == 0:
            return ClassOverview(
                total_students=0,
                scanned_students=0,
                last_scan_date=None,
                common_gaps=[],
                improvement_percentage=None,
            )

        # Get all active gap profiles for these students
        student_ids = [s.id for s in students]
        profiles_result = await self.db.execute(
            select(GapProfile).where(
                GapProfile.student_id.in_(student_ids),
                GapProfile.is_current == True,  # noqa: E712
            )
        )
        profiles = profiles_result.scalars().all()
        scanned_students = len(profiles)

        # Get last scan date
        last_scan_date = None
        if profiles:
            last_scan_date = max(p.created_at for p in profiles)

        # Get common gaps
        common_gaps = await self._get_common_gaps(list(profiles))

        # Calculate improvement (compare to 1 week ago)
        improvement = await self._calculate_improvement(teacher_id)

        return ClassOverview(
            total_students=total_students,
            scanned_students=scanned_students,
            last_scan_date=last_scan_date,
            common_gaps=common_gaps,
            improvement_percentage=improvement,
        )

    async def _get_common_gaps(self, profiles: list[GapProfile]) -> list[GapSummary]:
        """Identify most common gaps across profiles.

        Args:
            profiles: List of gap profiles

        Returns:
            List of gap summaries sorted by frequency
        """
        if not profiles:
            return []

        # Count gap node occurrences
        gap_counts: dict[UUID, int] = {}
        for profile in profiles:
            if profile.gap_nodes:
                for node_id in profile.gap_nodes:
                    gap_counts[node_id] = gap_counts.get(node_id, 0) + 1

        if not gap_counts:
            return []

        # Get top 5 most common gaps
        sorted_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Fetch node details
        node_ids = [node_id for node_id, _ in sorted_gaps]
        nodes_result = await self.db.execute(
            select(CurriculumNode).where(CurriculumNode.id.in_(node_ids))
        )
        nodes = {node.id: node for node in nodes_result.scalars().all()}

        # Build summaries
        summaries = []
        for node_id, count in sorted_gaps:
            if node_id in nodes:
                node = nodes[node_id]
                summaries.append(
                    GapSummary(
                        node_code=node.code,
                        node_title=node.title,
                        student_count=count,
                        severity=node.severity or 0,
                    )
                )

        return summaries

    async def _calculate_improvement(self, teacher_id: UUID) -> int | None:
        """Calculate class improvement percentage over last week.

        Args:
            teacher_id: Teacher's UUID

        Returns:
            Improvement percentage (0-100) or None if no historical data
        """
        # Get students
        students_result = await self.db.execute(
            select(Student.id).where(
                Student.teacher_id == teacher_id,
            )
        )
        student_ids = [s[0] for s in students_result.all()]

        if not student_ids:
            return None

        # Count current gaps
        current_result = await self.db.execute(
            select(func.count(GapProfile.id)).where(
                GapProfile.student_id.in_(student_ids),
                GapProfile.is_current == True,  # noqa: E712
            )
        )
        current_gap_count = current_result.scalar() or 0

        # Count gaps from 1 week ago
        week_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
        past_result = await self.db.execute(
            select(func.count(GapProfile.id)).where(
                GapProfile.student_id.in_(student_ids),
                GapProfile.created_at <= week_ago,
                GapProfile.created_at >= week_ago - timedelta(days=1),  # 1-day window
            )
        )
        past_gap_count = past_result.scalar() or 0

        if past_gap_count == 0:
            return None

        # Calculate improvement
        improvement = int(((past_gap_count - current_gap_count) / past_gap_count) * 100)
        return max(0, min(100, improvement))  # Clamp to 0-100

    async def get_student_report(self, student_id: UUID) -> StudentReport | None:
        """Get detailed report for individual student.

        Args:
            student_id: Student's UUID

        Returns:
            StudentReport or None if student not found
        """
        # Get student
        student_result = await self.db.execute(select(Student).where(Student.id == student_id))
        student = student_result.scalar_one_or_none()

        if not student:
            return None

        # Get active gap profile
        profile_result = await self.db.execute(
            select(GapProfile).where(
                GapProfile.student_id == student_id,
                GapProfile.is_current == True,  # noqa: E712
            )
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return StudentReport(
                student_name=student.first_name or "Student",
                scan_date=None,
                primary_gap=None,
                gap_list=[],
                recommended_actions=None,
                estimated_time=None,
            )

        # Get primary gap node
        primary_gap_title = None
        if profile.primary_gap_node:
            node_result = await self.db.execute(
                select(CurriculumNode).where(CurriculumNode.id == profile.primary_gap_node)
            )
            primary_node = node_result.scalar_one_or_none()
            if primary_node:
                primary_gap_title = f"{primary_node.code} - {primary_node.title}"

        # Get gap list
        gap_list = []
        if profile.gap_nodes:
            gap_nodes_result = await self.db.execute(
                select(CurriculumNode).where(CurriculumNode.id.in_(profile.gap_nodes))
            )
            gap_nodes = gap_nodes_result.scalars().all()
            gap_list = [f"{node.code} - {node.title}" for node in gap_nodes]

        # Estimate intervention time based on gap count and severity
        estimated_time = self._estimate_intervention_time(profile)

        return StudentReport(
            student_name=student.first_name or "Student",
            scan_date=profile.created_at,
            primary_gap=primary_gap_title,
            gap_list=gap_list,
            recommended_actions=self._generate_recommendations(profile),
            estimated_time=estimated_time,
        )

    def _estimate_intervention_time(self, profile: GapProfile) -> str:
        """Estimate time needed for intervention.

        Args:
            profile: Gap profile

        Returns:
            Time estimate string
        """
        gap_count = len(profile.gap_nodes) if profile.gap_nodes else 0

        if gap_count == 0:
            return "No intervention needed"
        elif gap_count <= 2:
            return "1-2 weeks of daily practice"
        elif gap_count <= 5:
            return "2-4 weeks of targeted support"
        else:
            return "4-8 weeks of intensive intervention"

    def _generate_recommendations(self, profile: GapProfile) -> str:
        """Generate actionable recommendations for teacher.

        Args:
            profile: Gap profile

        Returns:
            Recommendation text
        """
        if not profile.gap_nodes or len(profile.gap_nodes) == 0:
            return "Student is performing well! Continue current practice."

        # Default recommendations based on gap profile
        recommendations = []

        if profile.primary_gap_node:
            recommendations.append("Focus on primary gap first (root cause)")

        if profile.recommended_focus_node:
            recommendations.append("Use concrete materials and visual aids")

        if len(profile.gap_nodes) > 3:
            recommendations.append("Break into smaller daily lessons (10-15 min)")
        else:
            recommendations.append("Daily practice with real-world examples")

        recommendations.append("Check understanding before moving forward")

        return "\n".join(f"{i}. {rec}" for i, rec in enumerate(recommendations, 1))

    async def get_gap_breakdown(self, teacher_id: UUID) -> list[GapSummary]:
        """Get detailed breakdown of all gaps in class.

        Args:
            teacher_id: Teacher's UUID

        Returns:
            List of all gaps sorted by frequency and severity
        """
        # Get students
        students_result = await self.db.execute(
            select(Student.id).where(
                Student.teacher_id == teacher_id,
            )
        )
        student_ids = [s[0] for s in students_result.all()]

        if not student_ids:
            return []

        # Get all active profiles
        profiles_result = await self.db.execute(
            select(GapProfile).where(
                GapProfile.student_id.in_(student_ids),
                GapProfile.is_current == True,  # noqa: E712
            )
        )
        profiles = profiles_result.scalars().all()

        return await self._get_common_gaps(list(profiles))
