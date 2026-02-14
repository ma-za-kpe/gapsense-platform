"""
Curriculum Models

Represents the NaCCA prerequisite graph - GapSense's core IP.

Based on docs/specs/gapsense_data_model.sql
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CurriculumStrand(Base):
    """Top-level curriculum strands (Number, Algebra, Geometry, Data, Literacy)."""

    __tablename__ = "curriculum_strands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strand_number: Mapped[int] = mapped_column(
        SmallInteger, unique=True, nullable=False, comment="Strand number (1-5)"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Strand name (e.g., 'Number', 'Algebra')"
    )
    color_hex: Mapped[str | None] = mapped_column(
        String(7), nullable=True, comment="UI color code (#RRGGBB)"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("NOW()"), comment="Creation timestamp"
    )

    # Relationships
    sub_strands: Mapped[list[CurriculumSubStrand]] = relationship(
        back_populates="strand", cascade="all, delete-orphan"
    )
    nodes: Mapped[list[CurriculumNode]] = relationship(
        back_populates="strand", cascade="all, delete-orphan"
    )


class CurriculumSubStrand(Base):
    """Sub-strands within each strand."""

    __tablename__ = "curriculum_sub_strands"
    __table_args__ = (UniqueConstraint("strand_id", "sub_strand_number", "phase"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strand_id: Mapped[int] = mapped_column(ForeignKey("curriculum_strands.id"), nullable=False)
    sub_strand_number: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="Sub-strand number within strand"
    )
    phase: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="Phase: 'B1_B3', 'B4_B6', 'B7_B9'"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("NOW()"))

    # Relationships
    strand: Mapped[CurriculumStrand] = relationship(back_populates="sub_strands")
    nodes: Mapped[list[CurriculumNode]] = relationship(
        back_populates="sub_strand", cascade="all, delete-orphan"
    )


class CurriculumNode(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core curriculum nodes in the prerequisite graph.

    Each node represents a specific learning objective from NaCCA curriculum.
    Code format: B{grade}.{strand}.{sub_strand}.{content_standard}
    Example: B2.1.1.1 = Basic 2, Number (1), Counting (1), Content Standard 1
    """

    __tablename__ = "curriculum_nodes"
    __table_args__ = (
        CheckConstraint("severity >= 1 AND severity <= 5", name="check_severity_range"),
        CheckConstraint(
            "population_status IN ('skeleton', 'partial', 'full', 'validated')",
            name="check_population_status",
        ),
        Index("idx_curriculum_nodes_grade", "grade"),
        Index("idx_curriculum_nodes_severity", "severity", postgresql_ops={"severity": "DESC"}),
        Index("idx_curriculum_nodes_code", "code"),
    )

    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="Node code (e.g., 'B2.1.1.1')"
    )
    grade: Mapped[str] = mapped_column(
        String(5), nullable=False, comment="Grade level ('B1' through 'B9')"
    )

    strand_id: Mapped[int] = mapped_column(ForeignKey("curriculum_strands.id"), nullable=False)
    sub_strand_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_sub_strands.id"), nullable=False
    )
    content_standard_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="Human-readable title")
    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Full description of mastery"
    )

    severity: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="Severity rating (1-5, 5=most critical)"
    )
    severity_rationale: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Why this severity rating"
    )

    # Diagnostic configuration
    questions_required: Mapped[int] = mapped_column(
        SmallInteger, default=2, comment="Min questions to confirm mastery/gap"
    )
    confidence_threshold: Mapped[float] = mapped_column(
        default=0.80, comment="Confidence threshold for diagnosis"
    )

    # Ghana-specific evidence
    ghana_evidence: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="EGMA/NEA data, research citations"
    )

    # Population status
    population_status: Mapped[str] = mapped_column(
        String(20), default="skeleton", comment="Population status: skeleton/partial/full/validated"
    )

    # Relationships
    strand: Mapped[CurriculumStrand] = relationship(back_populates="nodes")
    sub_strand: Mapped[CurriculumSubStrand] = relationship(back_populates="nodes")

    prerequisites_as_target: Mapped[list[CurriculumPrerequisite]] = relationship(
        foreign_keys="CurriculumPrerequisite.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )
    prerequisites_as_source: Mapped[list[CurriculumPrerequisite]] = relationship(
        foreign_keys="CurriculumPrerequisite.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )

    misconceptions: Mapped[list[CurriculumMisconception]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )
    indicators: Mapped[list[CurriculumIndicator]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )


class CurriculumPrerequisite(Base):
    """Directed edges in the prerequisite graph.

    Represents prerequisite relationships between nodes.
    Example: B4.1.3.1 (fraction operations) requires B2.1.3.1 (fraction concept)
    """

    __tablename__ = "curriculum_prerequisites"
    __table_args__ = (
        UniqueConstraint("source_node_id", "target_node_id"),
        CheckConstraint("source_node_id != target_node_id", name="check_no_self_loop"),
        CheckConstraint(
            "relationship_type IN ('requires', 'strengthens', 'enables')",
            name="check_relationship_type",
        ),
        Index("idx_prerequisites_source", "source_node_id"),
        Index("idx_prerequisites_target", "target_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    source_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Source node (depends on target)",
    )
    target_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Target node (prerequisite)",
    )

    relationship_type: Mapped[str] = mapped_column(
        String(20), default="requires", comment="Type: 'requires', 'strengthens', 'enables'"
    )
    weight: Mapped[float] = mapped_column(default=1.0, comment="Edge weight for path analysis")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("NOW()"))

    # Relationships
    source_node: Mapped[CurriculumNode] = relationship(
        foreign_keys=[source_node_id], back_populates="prerequisites_as_source"
    )
    target_node: Mapped[CurriculumNode] = relationship(
        foreign_keys=[target_node_id], back_populates="prerequisites_as_target"
    )


class CurriculumIndicator(Base, UUIDPrimaryKeyMixin):
    """Learning indicators within each content standard."""

    __tablename__ = "curriculum_indicators"

    node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("curriculum_nodes.id", ondelete="CASCADE"), nullable=False
    )
    indicator_code: Mapped[str] = mapped_column(
        String(25), unique=True, nullable=False, comment="Indicator code (e.g., 'B1.1.1.1.1')"
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    # Diagnostic integration
    diagnostic_question_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="Question type: 'oral_counting', 'computation', 'word_problem'",
    )
    diagnostic_prompt_example: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Example diagnostic question"
    )

    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("NOW()"))

    # Relationships
    node: Mapped[CurriculumNode] = relationship(back_populates="indicators")
    error_patterns: Mapped[list[IndicatorErrorPattern]] = relationship(
        back_populates="indicator", cascade="all, delete-orphan"
    )


class IndicatorErrorPattern(Base):
    """Error patterns that reveal specific gaps."""

    __tablename__ = "indicator_error_patterns"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('critical', 'standard', 'minor')", name="check_error_severity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    indicator_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_indicators.id", ondelete="CASCADE"),
        nullable=False,
    )
    error_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(10), default="standard", comment="Severity: 'critical', 'standard', 'minor'"
    )
    indicates_gap_at: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id"),
        nullable=True,
        comment="Which node this error points to",
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("NOW()"))

    # Relationships
    indicator: Mapped[CurriculumIndicator] = relationship(back_populates="error_patterns")


class CurriculumMisconception(Base):
    """Common misconceptions at each curriculum node.

    Example: MC-B2.1.3.1-02 = "Larger denominator means larger fraction"
    """

    __tablename__ = "curriculum_misconceptions"
    __table_args__ = (
        # Primary key is the misconception ID string (not auto-increment)
    )

    id: Mapped[str] = mapped_column(
        String(30), primary_key=True, comment="Misconception ID (e.g., 'MC-B2.1.3.1-01')"
    )
    node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("curriculum_nodes.id", ondelete="CASCADE"), nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="What the misconception IS"
    )
    evidence: Mapped[str] = mapped_column(
        Text, nullable=False, comment="How it manifests (observable behavior)"
    )
    root_cause: Mapped[str] = mapped_column(
        Text, nullable=False, comment="WHY this misconception forms"
    )
    remediation_approach: Mapped[str] = mapped_column(Text, nullable=False, comment="How to fix it")

    frequency_estimate: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="e.g., '55% of students'"
    )
    source_citation: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Research source"
    )

    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("NOW()"))

    # Relationships
    node: Mapped[CurriculumNode] = relationship(back_populates="misconceptions")


class CascadePath(Base):
    """Pre-computed critical failure cascades.

    Example: "Place Value Collapse" - B1.1.1.1 → B2.1.1.1 → B4.1.1.1
    Affects ~55% of students.
    """

    __tablename__ = "cascade_paths"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Cascade name (e.g., 'Place Value Collapse')"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="e.g., 'Affects ~55% of students'"
    )

    diagnostic_entry_point: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id"),
        nullable=True,
        comment="Where to start testing for this cascade",
    )
    diagnostic_entry_question: Mapped[str | None] = mapped_column(Text, nullable=True)

    remediation_priority: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Priority: 'HIGHEST', 'HIGH', 'MEDIUM-HIGH', 'MEDIUM'"
    )

    node_sequence: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        comment="Ordered array of node IDs in the cascade",
    )

    created_at: Mapped[str] = mapped_column(String, nullable=False, server_default=text("NOW()"))
