"""
Adaptive Diagnostic Engine

Implements the adaptive question selection algorithm based on:
- Wolf/Aurino evidence-based principles
- Backward tracing to root gaps
- Cascade path detection
- Confidence-based mastery/gap determination
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.core.models import CurriculumNode, DiagnosticSession


class AdaptiveDiagnosticEngine:
    """Manages adaptive question selection during diagnostic sessions.

    Algorithm:
    1. START: Entry grade - 1 (B5 student → start at B4)
    2. SCREEN: Test priority screening nodes
    3. TRACE: Follow prerequisites backward when gaps detected
    4. ANCHOR: Stop at last mastered node
    5. CROSS-CHECK: Test different cascade if needed
    6. COMPLETE: Generate gap profile
    """

    # Priority screening nodes (high-severity, common gaps)
    SCREENING_NODES = [
        "B2.1.1.1",  # Place value to 1000
        "B1.1.2.2",  # Subtraction within 100
        "B2.1.2.2",  # Multiplication concept
        "B2.1.3.1",  # Fraction concept (half, quarter)
        "B3.1.3.1",  # Fraction equivalence
        "B4.1.3.1",  # Fraction operations
    ]

    # Minimum questions per node to confirm status
    MIN_QUESTIONS_PER_NODE = 2

    # Confidence threshold for mastery/gap determination
    CONFIDENCE_THRESHOLD = 0.80

    # Maximum questions before forcing completion
    MAX_QUESTIONS = 15

    def __init__(self, session: DiagnosticSession, db: AsyncSession):
        """Initialize diagnostic engine for a session.

        Args:
            session: Active diagnostic session
            db: Database session
        """
        self.session = session
        self.db = db

    async def get_next_node(self) -> CurriculumNode | None:
        """Determine next node to test based on session state.

        Returns:
            Next curriculum node to test, or None if session complete
        """
        # Check if we've hit max questions
        if self.session.total_questions >= self.MAX_QUESTIONS:
            return None

        # Phase 1: Screening (if just started)
        if self.session.total_questions < len(self.SCREENING_NODES) * self.MIN_QUESTIONS_PER_NODE:
            return await self._get_screening_node()

        # Phase 2: Backward tracing (if gap detected)
        if self.session.nodes_gap:
            return await self._get_prerequisite_node()

        # Phase 3: Cross-check different cascade
        if await self._should_cross_check():
            return await self._get_cross_check_node()

        # All done
        return None

    async def _get_screening_node(self) -> CurriculumNode | None:
        """Get next screening node to test.

        Returns:
            Screening node, or None if screening complete
        """
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode

        # Find screening nodes not yet sufficiently tested
        for node_code in self.SCREENING_NODES:
            # Get node
            result = await self.db.execute(
                select(CurriculumNode).where(CurriculumNode.code == node_code)
            )
            node = result.scalar_one_or_none()

            if not node:
                continue

            # Check if needs more questions
            questions_asked = self._count_questions_for_node(node.id)
            if questions_asked < self.MIN_QUESTIONS_PER_NODE:
                return node

        return None

    async def _get_prerequisite_node(self) -> CurriculumNode | None:
        """Trace backward to prerequisite of deepest gap.

        Returns:
            Prerequisite node to test, or None if reached bottom
        """
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode, CurriculumPrerequisite

        # Get deepest gap (highest severity among gap nodes)
        if not self.session.nodes_gap:
            return None

        # Find the gap node with highest severity
        result = await self.db.execute(
            select(CurriculumNode)
            .where(CurriculumNode.id.in_(self.session.nodes_gap))
            .order_by(CurriculumNode.severity.desc())
        )
        deepest_gap = result.scalars().first()

        if not deepest_gap:
            return None

        # Get its prerequisites (target nodes where source is the current node)
        result = await self.db.execute(
            select(CurriculumNode)
            .join(
                CurriculumPrerequisite,
                CurriculumPrerequisite.target_node_id == CurriculumNode.id,
            )
            .where(CurriculumPrerequisite.source_node_id == deepest_gap.id)
            .order_by(CurriculumNode.severity.desc())
        )
        prerequisites = result.scalars().all()

        # Find untested prerequisite
        for prereq in prerequisites:
            if prereq.id not in self.session.nodes_tested:
                return prereq

        return None

    async def _get_cross_check_node(self) -> CurriculumNode | None:
        """Get node from different cascade to cross-check.

        Returns:
            Cross-check node, or None if not needed
        """
        from sqlalchemy import select

        from gapsense.core.models import CascadePath, CurriculumNode

        if not self.session.root_gap_node_id:
            return None

        # Get the cascade path containing the root gap
        cascade_result = await self.db.execute(select(CascadePath))
        all_cascades = cascade_result.scalars().all()

        root_gap_cascade = None
        for cascade in all_cascades:
            if self.session.root_gap_node_id in cascade.node_sequence:
                root_gap_cascade = cascade
                break

        if not root_gap_cascade:
            return None

        # Find a different cascade to cross-check
        for cascade in all_cascades:
            if cascade.id == root_gap_cascade.id:
                continue  # Skip same cascade

            # Get entry point node from different cascade
            if cascade.diagnostic_entry_point:
                node_result = await self.db.execute(
                    select(CurriculumNode).where(
                        CurriculumNode.id == cascade.diagnostic_entry_point
                    )
                )
                entry_node = node_result.scalar_one_or_none()

                # Only use if not already tested
                if entry_node and entry_node.id not in self.session.nodes_tested:
                    return entry_node

        return None

    async def _should_cross_check(self) -> bool:
        """Determine if cross-checking is needed.

        Returns:
            True if should test different cascade
        """
        # Cross-check if:
        # - Root gap identified (severity 5)
        # - Sufficient questions asked (>= 8)
        # - Haven't cross-checked yet

        if not self.session.root_gap_node_id:
            return False

        from sqlalchemy import select

        from gapsense.core.models import CascadePath, CurriculumNode

        result = await self.db.execute(
            select(CurriculumNode).where(CurriculumNode.id == self.session.root_gap_node_id)
        )
        root_gap = result.scalar_one_or_none()

        if not root_gap or root_gap.severity < 5:
            return False

        if self.session.total_questions < 8:
            return False

        # Check if already cross-checked by seeing if cascade_path_id is set
        if self.session.cascade_path_id is not None:
            return False  # Already identified primary cascade

        # Check if there are other cascades available to cross-check
        result = await self.db.execute(select(CascadePath))
        all_cascades = result.scalars().all()

        # Need at least 2 cascades for cross-checking
        return len(all_cascades) >= 2

    def _count_questions_for_node(self, node_id: UUID) -> int:
        """Count questions asked for a specific node.

        Args:
            node_id: Curriculum node ID

        Returns:
            Number of questions asked for this node
        """
        return self.session.nodes_tested.count(node_id) if self.session.nodes_tested else 0

    async def identify_cascade_path(self, node_id: UUID) -> int | None:
        """Identify which cascade path a node belongs to.

        Args:
            node_id: Node to check

        Returns:
            Cascade path ID if found, None otherwise
        """
        from sqlalchemy import select

        from gapsense.core.models import CascadePath

        result = await self.db.execute(select(CascadePath))
        all_cascades = result.scalars().all()

        for cascade in all_cascades:
            if node_id in cascade.node_sequence:
                return cascade.id

        return None

    async def update_session_state(self, node_id: UUID, is_correct: bool) -> dict[str, str | float]:
        """Update session state after answer submission.

        Args:
            node_id: Node that was tested
            is_correct: Whether answer was correct

        Returns:
            Dict with node_status and confidence
        """
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode

        # Get node
        result = await self.db.execute(select(CurriculumNode).where(CurriculumNode.id == node_id))
        node = result.scalar_one_or_none()

        if not node:
            return {"node_status": "unknown", "confidence": 0.0}

        # Update tested nodes
        if not self.session.nodes_tested:
            self.session.nodes_tested = []
        self.session.nodes_tested.append(node_id)

        # Count questions for this node
        questions_for_node = self._count_questions_for_node(node_id)

        # Determine node status
        if questions_for_node < self.MIN_QUESTIONS_PER_NODE:
            # Not enough data yet
            return {"node_status": "uncertain", "confidence": 0.5}

        # Calculate correctness rate for this node
        # TODO: Track individual question results properly
        # For now, use simplified logic

        if is_correct:
            # Mark as mastered if consistently correct
            if node_id not in self.session.nodes_mastered:
                if not self.session.nodes_mastered:
                    self.session.nodes_mastered = []
                self.session.nodes_mastered.append(node_id)

            # Remove from gaps if was there
            if self.session.nodes_gap and node_id in self.session.nodes_gap:
                self.session.nodes_gap.remove(node_id)

            return {"node_status": "mastered", "confidence": 0.85}
        else:
            # Mark as gap if consistently incorrect
            if node_id not in self.session.nodes_gap:
                if not self.session.nodes_gap:
                    self.session.nodes_gap = []
                self.session.nodes_gap.append(node_id)

            # Update root gap if higher severity
            if not self.session.root_gap_node_id or (
                await self._is_higher_severity(node_id, self.session.root_gap_node_id)
            ):
                self.session.root_gap_node_id = node_id
                self.session.root_gap_confidence = 0.85

            return {"node_status": "gap", "confidence": 0.85}

    async def _is_higher_severity(self, node_a_id: UUID, node_b_id: UUID) -> bool:
        """Check if node A has higher severity than node B.

        Args:
            node_a_id: First node ID
            node_b_id: Second node ID

        Returns:
            True if node A severity >= node B severity
        """
        from sqlalchemy import select

        from gapsense.core.models import CurriculumNode

        result = await self.db.execute(
            select(CurriculumNode).where(CurriculumNode.id.in_([node_a_id, node_b_id]))
        )
        nodes = {node.id: node for node in result.scalars().all()}

        if node_a_id not in nodes or node_b_id not in nodes:
            return False

        return nodes[node_a_id].severity >= nodes[node_b_id].severity

    async def should_complete_session(self) -> bool:
        """Determine if session should be completed.

        Returns:
            True if enough data collected to generate gap profile
        """
        # Complete if:
        # 1. Hit max questions, OR
        # 2. Root gap identified with high confidence, OR
        # 3. All screening nodes tested and no gaps found

        if self.session.total_questions >= self.MAX_QUESTIONS:
            return True

        if (
            self.session.root_gap_node_id
            and self.session.root_gap_confidence
            and self.session.root_gap_confidence >= self.CONFIDENCE_THRESHOLD
        ):
            return True

        # Check if all screening complete and no gaps
        return (
            self.session.total_questions >= len(self.SCREENING_NODES) * self.MIN_QUESTIONS_PER_NODE
            and not self.session.nodes_gap
        )
