"""Tests for model identity, timestamp, privacy, and default invariants."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import configure_mappers

from gapsense.core.models import Parent, Teacher

configure_mappers()


def test_model_mixins_generate_safe_in_memory_defaults() -> None:
    """New records receive identity, timestamps, and consent-safe defaults."""
    parent = Parent(phone="+233500000001")

    assert parent.id is not None
    assert parent.created_at is not None
    assert parent.updated_at == parent.created_at
    assert parent.opted_out is False


def test_model_mixins_preserve_explicit_values() -> None:
    """Callers can restore persisted identity, timestamps, and consent state."""
    identifier = uuid4()
    timestamp = datetime(2026, 7, 22, tzinfo=UTC)

    parent = Parent(
        phone="+256700000001",
        id=identifier,
        created_at=timestamp,
        updated_at=timestamp,
        opted_out=True,
    )

    assert parent.id == identifier
    assert parent.created_at == timestamp
    assert parent.updated_at == timestamp
    assert parent.opted_out is True


def test_soft_delete_state_changes_without_hard_deletion() -> None:
    """Soft deletion remains observable without removing the record."""
    teacher = Teacher(
        school_id=uuid4(),
        first_name="Amina",
        last_name="Nabirye",
        phone="+256700000002",
    )

    assert teacher.is_deleted is False

    teacher.soft_delete()

    assert teacher.is_deleted is True
    assert teacher.deleted_at is not None
