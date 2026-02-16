"""
Tests for school matcher integration in teacher onboarding flow.

Ensures teachers can find and use existing schools instead of creating duplicates.
"""

from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import School, Teacher
from gapsense.engagement.teacher_flows import TeacherFlowExecutor
from gapsense.engagement.whatsapp_client import WhatsAppClient


async def test_teacher_finds_exact_school_match(db_session: AsyncSession):
    """Teacher types exact school name → uses existing school."""
    # Create existing school
    existing_school = School(
        name="St. Mary's JHS, Accra",
        district_id=1,
        school_type="jhs",
        is_active=True,
    )
    db_session.add(existing_school)
    await db_session.commit()

    teacher = Teacher(
        phone="+233501111111",
        first_name="Test",
        last_name="Teacher",
        conversation_state={
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        },
        is_active=True,
    )
    db_session.add(teacher)
    await db_session.commit()

    # Mock WhatsApp client
    with patch(
        "gapsense.engagement.whatsapp_client.WhatsAppClient.from_settings"
    ) as mock_client_class:
        mock_client = AsyncMock(spec=WhatsAppClient)
        mock_client.send_text_message = AsyncMock(return_value="wamid.123")
        mock_client.send_button_message = AsyncMock(return_value="wamid.123")
        mock_client_class.return_value = mock_client

        executor = TeacherFlowExecutor(db=db_session)

        # Teacher types exact school name
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="St. Mary's JHS, Accra",
            message_id="msg-123",
        )

        await db_session.refresh(teacher)

        # Should find existing school (not create new one)
        assert result.message_sent is True
        assert teacher.school_id == existing_school.id


async def test_teacher_finds_fuzzy_school_match(db_session: AsyncSession):
    """Teacher types school name with different punctuation → finds existing school."""
    # Create existing school
    existing_school = School(
        name="St. Mary's JHS, Accra",
        district_id=1,
        school_type="jhs",
        is_active=True,
    )
    db_session.add(existing_school)
    await db_session.commit()

    teacher = Teacher(
        phone="+233502222222",
        first_name="Test",
        last_name="Teacher",
        conversation_state={
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        },
        is_active=True,
    )
    db_session.add(teacher)
    await db_session.commit()

    with patch(
        "gapsense.engagement.whatsapp_client.WhatsAppClient.from_settings"
    ) as mock_client_class:
        mock_client = AsyncMock(spec=WhatsAppClient)
        mock_client.send_text_message = AsyncMock(return_value="wamid.123")
        mock_client.send_button_message = AsyncMock(return_value="wamid.123")
        mock_client_class.return_value = mock_client

        executor = TeacherFlowExecutor(db=db_session)

        # Teacher types school name without punctuation
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="St Marys JHS Accra",  # No apostrophe, no comma
            message_id="msg-456",
        )

        await db_session.refresh(teacher)

        # Should find existing school through fuzzy matching
        assert result.message_sent is True
        assert teacher.school_id == existing_school.id


async def test_teacher_creates_new_school_when_no_match(db_session: AsyncSession):
    """Teacher types unique school name → creates new school."""
    # Create unrelated school
    other_school = School(
        name="St. Paul's JHS, Accra",
        district_id=1,
        school_type="jhs",
        is_active=True,
    )
    db_session.add(other_school)
    await db_session.commit()

    teacher = Teacher(
        phone="+233503333333",
        first_name="Test",
        last_name="Teacher",
        conversation_state={
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        },
        is_active=True,
    )
    db_session.add(teacher)
    await db_session.commit()

    with patch(
        "gapsense.engagement.whatsapp_client.WhatsAppClient.from_settings"
    ) as mock_client_class:
        mock_client = AsyncMock(spec=WhatsAppClient)
        mock_client.send_text_message = AsyncMock(return_value="wamid.123")
        mock_client.send_button_message = AsyncMock(return_value="wamid.123")
        mock_client_class.return_value = mock_client

        executor = TeacherFlowExecutor(db=db_session)

        # Teacher types completely different school name
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="Wesley Girls JHS, Cape Coast",
            message_id="msg-789",
        )

        await db_session.refresh(teacher)

        # Should create new school (not match St. Paul's)
        assert result.message_sent is True
        assert teacher.school_id is not None
        assert teacher.school_id != other_school.id
