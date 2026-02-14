"""
Unit Tests for SQLAlchemy Models

Tests for model structure, relationships, and constraints.
"""

from datetime import datetime
from uuid import uuid4

from gapsense.core.models import (
    CurriculumNode,
    CurriculumStrand,
    Parent,
    Student,
)


def test_curriculum_strand_creation():
    """Test CurriculumStrand model creation."""
    strand = CurriculumStrand(
        strand_number=1,
        name="Number",
        color_hex="#2563EB",
        description="Counting, representation, operations",
    )

    assert strand.strand_number == 1
    assert strand.name == "Number"
    assert strand.color_hex == "#2563EB"


def test_curriculum_node_creation():
    """Test CurriculumNode model creation."""
    node_id = uuid4()
    node = CurriculumNode(
        id=node_id,
        code="B2.1.1.1",
        grade="B2",
        strand_id=1,
        sub_strand_id=1,
        content_standard_number=1,
        title="Counting to 100",
        description="Student can count from 1 to 100",
        severity=5,
        questions_required=2,
        confidence_threshold=0.80,
        population_status="full",
    )

    assert node.id == node_id
    assert node.code == "B2.1.1.1"
    assert node.grade == "B2"
    assert node.severity == 5
    assert node.population_status == "full"


def test_uuid_primary_key_mixin():
    """Test UUIDPrimaryKeyMixin generates UUIDs."""
    node = CurriculumNode(
        code="B1.1.1.1",
        grade="B1",
        strand_id=1,
        sub_strand_id=1,
        content_standard_number=1,
        title="Test",
        description="Test",
        severity=1,
    )

    # UUID should be auto-generated
    assert node.id is not None
    assert len(str(node.id)) == 36  # UUID format


def test_timestamp_mixin():
    """Test TimestampMixin sets created_at and updated_at."""
    node = CurriculumNode(
        code="B1.1.1.1",
        grade="B1",
        strand_id=1,
        sub_strand_id=1,
        content_standard_number=1,
        title="Test",
        description="Test",
        severity=1,
    )

    # Timestamps should be set (in memory, not DB default)
    assert isinstance(node.created_at, datetime)
    assert isinstance(node.updated_at, datetime)


def test_parent_model():
    """Test Parent model with Wolf/Aurino dignity-first fields."""
    parent = Parent(
        phone="+233501234567", preferred_name="Akosua", preferred_language="tw", opted_in=True
    )

    assert parent.phone == "+233501234567"
    assert parent.preferred_name == "Akosua"
    assert parent.preferred_language == "tw"
    assert parent.opted_in is True


def test_student_model():
    """Test Student model with minimal data collection."""
    parent_id = uuid4()
    student = Student(
        first_name="Kwame",
        current_grade="B3",
        primary_parent_id=parent_id,
        home_language="tw",
        school_language="English",
    )

    assert student.first_name == "Kwame"
    assert student.current_grade == "B3"
    assert student.primary_parent_id == parent_id
    assert student.home_language == "tw"


def test_soft_delete_mixin():
    """Test SoftDeleteMixin soft delete functionality."""
    from gapsense.core.models import Teacher

    teacher = Teacher(
        school_id=uuid4(), first_name="Akua", last_name="Mensah", phone="+233501234567"
    )

    # Initially not deleted
    assert teacher.is_deleted is False
    assert teacher.deleted_at is None

    # Soft delete
    teacher.soft_delete()

    # Should be marked as deleted
    assert teacher.is_deleted is True
    assert teacher.deleted_at is not None
    assert isinstance(teacher.deleted_at, datetime)


def test_curriculum_node_severity_range():
    """Test CurriculumNode severity is within valid range 1-5."""
    # Valid severity
    node_valid = CurriculumNode(
        code="B1.1.1.1",
        grade="B1",
        strand_id=1,
        sub_strand_id=1,
        content_standard_number=1,
        title="Test",
        description="Test",
        severity=3,
    )
    assert node_valid.severity == 3

    # Edge cases - should be valid in-memory
    node_min = CurriculumNode(
        code="B1.1.1.2",
        grade="B1",
        strand_id=1,
        sub_strand_id=1,
        content_standard_number=1,
        title="Test",
        description="Test",
        severity=1,
    )
    assert node_min.severity == 1

    node_max = CurriculumNode(
        code="B1.1.1.3",
        grade="B1",
        strand_id=1,
        sub_strand_id=1,
        content_standard_number=1,
        title="Test",
        description="Test",
        severity=5,
    )
    assert node_max.severity == 5


def test_parent_dignity_first_fields():
    """Test Parent model respects Wolf/Aurino dignity-first principles."""
    parent = Parent(
        phone="+233501234567",
        preferred_name="Mama Ama",
        preferred_language="tw",
        literacy_level="semi_literate",
        opted_in=True,
    )

    # Verify minimal data collection
    assert parent.phone == "+233501234567"
    assert parent.preferred_name == "Mama Ama"
    assert parent.preferred_language == "tw"

    # Sensitive field exists but should never be shared externally (per model comment)
    assert parent.literacy_level == "semi_literate"

    # Opt-in compliance
    assert parent.opted_in is True
    assert parent.opted_out is False


def test_student_dignity_first_minimal_collection():
    """Test Student model collects minimal data only."""
    student = Student(
        first_name="Abena",  # Only first name required
        current_grade="B4",
        primary_parent_id=uuid4(),
    )

    # Required fields
    assert student.first_name == "Abena"
    assert student.current_grade == "B4"

    # Optional fields should default to None
    assert student.age is None
    assert student.gender is None
    assert student.school_id is None

    # Privacy: no last name field exists
    assert not hasattr(student, "last_name")
