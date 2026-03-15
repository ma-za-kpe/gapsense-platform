"""
WhatsApp Webhook Handlers (Multi-Provider)

Handles webhook verification (GET) and incoming messages (POST).
Supports both Meta WhatsApp Cloud API and Twilio WhatsApp webhooks
via the webhook adapter normalization layer.
"""
# ruff: noqa: B008 - FastAPI Depends in function defaults is standard pattern

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select

from gapsense.config import settings
from gapsense.core.database import get_db
from gapsense.core.models import Parent, Teacher
from gapsense.engagement.flow_executor import FlowExecutor, FlowResult
from gapsense.engagement.teacher_flows import TeacherFlowExecutor, TeacherFlowResult
from gapsense.engagement.whatsapp.webhook_adapter import normalize_webhook

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])


@router.get("", response_class=Response)
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> Response:
    """Verify WhatsApp webhook with Meta.

    Meta sends a GET request with:
    - hub.mode: "subscribe"
    - hub.verify_token: Your verification token (from settings)
    - hub.challenge: Random string to echo back

    Returns:
        Challenge string if verification succeeds

    Raises:
        HTTPException: 403 if verify token doesn't match, 400 if params missing
    """
    logger.info(f"Webhook verification request received. Mode: {hub_mode}")

    # Verify the token matches our configured token
    if hub_verify_token != settings.WHATSAPP_VERIFY_TOKEN:
        logger.warning(
            f"Webhook verification failed. Expected: {settings.WHATSAPP_VERIFY_TOKEN}, "
            f"Received: {hub_verify_token}"
        )
        raise HTTPException(status_code=403, detail="Invalid verify token")

    # Verify the mode is "subscribe"
    if hub_mode != "subscribe":
        logger.warning(f"Webhook verification failed. Invalid mode: {hub_mode}")
        raise HTTPException(status_code=400, detail="Invalid hub.mode")

    logger.info("Webhook verification successful")
    return Response(content=hub_challenge, media_type="text/plain")


@router.post("")
async def handle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle incoming WhatsApp messages and status updates.

    Supports both Meta and Twilio webhook formats via the normalize_webhook adapter.
    Meta sends JSON, Twilio sends form-encoded data — both are normalized to
    Meta's format before processing.

    Returns:
        Always returns {"status": "received"} or {"status": "ignored"}
        to prevent provider retries

    Note:
        This endpoint must respond within 20 seconds or Meta will retry.
        Complex processing should be offloaded to async queues (SQS).
    """
    # Normalize webhook from any provider to Meta-compatible format
    body = await normalize_webhook(request)

    if body is None:
        logger.warning("Failed to parse or normalize webhook body")
        return {"status": "received"}

    # Log the webhook for debugging
    logger.info(f"Webhook received: {body}")

    # Ignore non-WhatsApp webhooks
    if body.get("object") != "whatsapp_business_account":
        logger.info(f"Ignoring non-WhatsApp webhook: {body.get('object')}")
        return {"status": "ignored"}

    # Extract entries (should always be a list)
    entries = body.get("entry", [])
    if not entries:
        logger.warning("Webhook has no entries")
        return {"status": "received"}

    # Process each entry
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            if change.get("field") != "messages":
                continue

            value = change.get("value", {})

            # Handle inbound messages
            messages = value.get("messages", [])
            for message in messages:
                await _handle_message(message, value, db)

            # Handle status updates (delivered, read, failed)
            statuses = value.get("statuses", [])
            for status in statuses:
                await _handle_status_update(status)

    return {"status": "received"}


async def _handle_message(
    message: dict[str, Any], _value: dict[str, Any], db: AsyncSession
) -> None:
    """Handle an inbound WhatsApp message.

    Args:
        message: Message object from webhook
        _value: Parent value object with metadata (reserved for future use)
        db: Database session

    Implementation:
        1. Detect user type (teacher or parent) by phone lookup
        2. Get or create user entity
        3. Route to appropriate flow executor
        4. Flow executor sends response via WhatsAppClient
    """
    message_type = message.get("type")
    from_number = message.get("from")
    message_id = message.get("id")

    # Validate required fields
    if not message_type or not from_number or not message_id:
        logger.warning(f"Incomplete message data: {message}")
        return

    logger.info(f"Received {message_type} message from {from_number} (ID: {message_id})")

    # Extract message content based on type
    content = _extract_message_content(message)

    logger.debug(f"Message content: {content}")

    try:
        # Detect user type and route to appropriate executor
        user_type, user = await _detect_user_type(db, from_number)

        result: TeacherFlowResult | FlowResult
        if user_type == "teacher":
            # Route all teacher messages through TeacherFlowExecutor
            # (including images for exercise book scanning with student selection)
            logger.info(f"Routing to TeacherFlowExecutor for {from_number}")
            teacher_executor = TeacherFlowExecutor(db=db)
            result = await teacher_executor.process_teacher_message(
                teacher=user,  # type: ignore[arg-type]
                message_type=message_type,
                message_content=content,
                message_id=message_id,
            )
        elif user_type == "parent":
            # Special handling for parent voice messages (Micro-Coaching)
            if message_type == "voice":
                await _handle_parent_voice(user, content, db)  # type: ignore[arg-type]
                return

            logger.info(f"Routing to ParentFlowExecutor for {from_number}")
            parent_executor = FlowExecutor(db=db)
            result = await parent_executor.process_message(
                parent=user,  # type: ignore[arg-type]
                message_type=message_type,
                message_content=content,
                message_id=message_id,
            )
        else:
            # Unknown user - will be handled by role selection logic
            logger.warning(f"Unknown user type for {from_number}")
            return

        # Log result
        if result.error:
            logger.error(
                f"Flow execution error for {from_number}: {result.error}",
                extra={
                    "flow": result.flow_name,
                    "user_type": user_type,
                    "message_id": message_id,
                },
            )
        else:
            logger.info(
                f"Flow executed: {result.flow_name} (completed: {result.completed})",
                extra={
                    "flow": result.flow_name,
                    "next_step": result.next_step,
                    "message_sent": result.message_sent,
                    "user_type": user_type,
                },
            )

    except Exception as e:
        logger.error(
            f"Failed to handle message from {from_number}: {e}",
            exc_info=True,
            extra={"message_id": message_id, "message_type": message_type},
        )


async def _detect_user_type(
    db: AsyncSession, phone: str
) -> tuple[str | None, Teacher | Parent | None]:
    """Detect whether user is a teacher or parent by phone lookup.

    Args:
        db: Database session
        phone: WhatsApp phone number

    Returns:
        Tuple of (user_type, user_entity) where:
        - user_type: "teacher", "parent", or None
        - user_entity: Teacher or Parent instance, or None

    Logic:
        1. Check if phone exists in teachers table
        2. If not, check if phone exists in parents table
        3. If not, create new parent (default for unknown users)

    Note:
        For MVP, unknown users default to parent flow.
        Teachers must be manually registered in system first.
    """
    try:
        phone = _validate_phone(phone)
    except ValueError as e:
        logger.warning(f"Invalid phone number: {e}")
        return None, None

    # Check if teacher
    stmt_teacher = select(Teacher).where(Teacher.phone == phone).where(Teacher.is_active == True)  # noqa: E712
    result = await db.execute(stmt_teacher)
    teacher = result.scalar_one_or_none()

    if teacher:
        logger.debug(f"Found existing teacher: {phone}")
        return "teacher", teacher

    # Check if parent (exclude opted-out parents)
    stmt_parent = select(Parent).where(Parent.phone == phone).where(Parent.opted_out == False)  # noqa: E712
    result_parent = await db.execute(stmt_parent)
    existing_parent = result_parent.scalar_one_or_none()

    if existing_parent:
        logger.debug(f"Found existing parent: {phone}")
        return "parent", existing_parent

    # Check if parent exists but opted out
    stmt_opted_out = select(Parent).where(Parent.phone == phone).where(Parent.opted_out == True)  # noqa: E712
    result_opted_out = await db.execute(stmt_opted_out)
    opted_out_parent = result_opted_out.scalar_one_or_none()

    if opted_out_parent:
        logger.info(f"Parent {phone} is opted out, ignoring message")
        return None, None  # Don't route opted-out parents

    # Unknown user - create as parent (default)
    logger.info(f"Unknown user, creating as parent: {phone}")
    try:
        new_parent = Parent(phone=phone)
        db.add(new_parent)
        await db.commit()
        await db.refresh(new_parent)
        return "parent", new_parent
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create parent {phone}: {e}", exc_info=True)
        return None, None


def _validate_phone(phone: str) -> str:
    """Validate and sanitize WhatsApp phone number.

    Args:
        phone: Raw phone number from webhook

    Returns:
        Sanitized phone number

    Raises:
        ValueError: If phone number is invalid

    Validation rules:
        - Must start with + (E.164 format)
        - Must be between 8 and 20 characters
        - Must contain only digits after +
        - No whitespace allowed
    """
    # Strip whitespace
    phone = phone.strip()

    # Check empty
    if not phone:
        raise ValueError("Phone number cannot be empty")

    # Check format (E.164 international format)
    if not phone.startswith("+"):
        raise ValueError(f"Phone number must start with + (E.164 format): {phone}")

    # Check length
    if len(phone) < 8 or len(phone) > 20:
        raise ValueError(f"Phone number length invalid (must be 8-20 chars): {phone}")

    # Check contains only digits after +
    if not phone[1:].isdigit():
        raise ValueError(f"Phone number must contain only digits after +: {phone}")

    return phone


async def _handle_status_update(status: dict[str, Any]) -> None:
    """Handle message delivery status update.

    Args:
        status: Status object from webhook (delivered, read, failed)

    Note:
        For MVP Week 1, this is a placeholder that logs the status.
        Full implementation will update ParentInteraction records.
    """
    message_id = status.get("id")
    status_value = status.get("status")
    recipient = status.get("recipient_id")

    logger.info(f"Status update for message {message_id}: {status_value} (recipient: {recipient})")

    # TODO: Week 1 Implementation
    # Update ParentInteraction record with delivery status


def _extract_message_content(message: dict[str, Any]) -> str | dict[str, Any]:
    """Extract content from message based on type.

    Args:
        message: Message object from webhook

    Returns:
        Extracted content (text string or structured dict for interactive messages)
    """
    message_type = message.get("type")

    if message_type == "text":
        text_body: str = message.get("text", {}).get("body", "")
        return text_body

    elif message_type == "interactive":
        interactive = message.get("interactive", {})
        interactive_type = interactive.get("type")

        if interactive_type == "button_reply":
            button_data: dict[str, Any] = interactive.get("button_reply", {})
            return button_data
        elif interactive_type == "list_reply":
            list_data: dict[str, Any] = interactive.get("list_reply", {})
            return list_data

    elif message_type == "image":
        image_data: dict[str, Any] = message.get("image", {})
        return image_data

    elif message_type == "voice":
        voice_data: dict[str, Any] = message.get("voice", {})
        return voice_data

    return ""


async def _handle_teacher_image(
    teacher: Teacher, image_content: dict[str, Any], db: AsyncSession
) -> None:
    """Handle exercise book image from teacher (Task 6: ExerciseBookScanner).

    Routes teacher image uploads to ExerciseBookScanner which:
    1. Downloads image from WhatsApp
    2. Uploads image to S3
    3. Enqueues image_analyze task
    4. Sends acknowledgment to teacher

    Args:
        teacher: Teacher instance
        image_content: Image metadata from webhook
        db: Database session
    """
    from sqlalchemy import select

    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.core.models import Student
    from gapsense.engagement.exercise_book_scanner import ExerciseBookScanner
    from gapsense.engagement.whatsapp import get_whatsapp_client
    from gapsense.services.guard_service import GuardService
    from gapsense.services.media_service import MediaService
    from gapsense.services.worker_service import WorkerService

    try:
        # Extract media info (URL for Twilio, ID for Meta)
        media_id = image_content.get("url") or image_content.get("id")
        mime_type = image_content.get("mime_type", "image/jpeg")

        if not media_id:
            logger.warning(f"No media ID/URL in image content: {image_content}")
            return

        # Download image from WhatsApp
        client = get_whatsapp_client()
        image_bytes = await client.download_media(media_id=media_id)

        # Get teacher's most recent student (or first student)
        # TODO: In production, might want to ask teacher which student
        stmt = (
            select(Student)
            .where(Student.teacher_id == teacher.id)
            .order_by(Student.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()

        if not student:
            # No students yet - send message asking teacher to register student first
            await client.send_text_message(
                to=teacher.phone,
                text="⚠️ Please register at least one student first before uploading exercise books.",
            )
            return

        # Initialize ExerciseBookScanner with services
        ai_client = AsyncAIClient(anthropic_api_key=settings.ANTHROPIC_API_KEY)
        prompt_service = PromptService(settings=settings)
        guard_service = GuardService(ai_client=ai_client, prompt_service=prompt_service)
        media_service = MediaService(settings=settings)
        worker_service = WorkerService(ai_client=ai_client, media_service=media_service, guard_service=guard_service, prompt_service=prompt_service, settings=settings, db=db)

        scanner = ExerciseBookScanner(
            db=db,
            media_service=media_service,
            worker_service=worker_service,
            guard_service=guard_service,
            ai_client=ai_client,
            prompt_service=prompt_service,
        )

        # Process image
        result = await scanner.handle_image_message(
            teacher=teacher,
            student=student,
            image_bytes=image_bytes,
            filename=f"exercise_book_{media_id[:8]}.jpg",
            content_type=mime_type,
            country=teacher.school.district.region.country_code if teacher.school else "GH",
        )

        if result.success:
            logger.info(f"Exercise book scan queued: {result.s3_key} for student {student.id}")
        else:
            logger.error(f"Exercise book scan failed: {result.error}")
            await client.send_text_message(
                to=teacher.phone,
                text=f"⚠️ Failed to process exercise book: {result.error}",
            )

    except Exception as e:
        logger.error(f"Failed to handle teacher image: {e}", exc_info=True)
        # Send error message to teacher
        try:
            client = get_whatsapp_client()
            await client.send_text_message(
                to=teacher.phone,
                text="⚠️ Sorry, we encountered an error processing your image. Please try again.",
            )
        except Exception:
            pass  # Don't fail if error message fails


async def _handle_teacher_conversation(teacher: Teacher, message: str, db: AsyncSession) -> None:
    """Handle teacher text message (Task 8: TeacherConversation).

    Routes teacher text messages to TeacherConversationPartner which:
    1. Analyzes question with class gap data
    2. Generates pedagogical response
    3. Sends formatted response via WhatsApp
    """
    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.engagement.teacher_conversation import TeacherConversationPartner

    try:
        # Initialize services
        ai_client = AsyncAIClient()
        prompt_service = PromptService()

        # Initialize conversation partner
        conversation = TeacherConversationPartner(
            db=db,
            ai_client=ai_client,
            prompt_service=prompt_service,
        )

        # Handle conversation turn
        from gapsense.core.country_utils import get_country_from_teacher

        result = await conversation.handle_teacher_message(
            teacher=teacher,
            message=message,
            country=get_country_from_teacher(teacher),
            language="en",
        )

        if not result.success:
            logger.warning(f"Teacher conversation failed: {result.error}")

    except Exception as e:
        logger.error(f"Failed to handle teacher conversation: {e}", exc_info=True)


async def _handle_parent_voice(
    parent: Parent, voice_content: dict[str, Any], db: AsyncSession
) -> None:
    """Handle parent voice message (Task 9: VoiceMicroCoaching).

    Routes parent voice notes to VoiceMicroCoaching which:
    1. Downloads audio from WhatsApp
    2. Uploads audio to S3
    3. Enqueues voice_transcribe task
    4. Sends acknowledgment

    Args:
        parent: Parent instance
        voice_content: Voice audio metadata from webhook
        db: Database session
    """
    from sqlalchemy import select

    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.core.models import Student
    from gapsense.engagement.voice_micro_coaching import VoiceMicroCoaching
    from gapsense.engagement.whatsapp import get_whatsapp_client
    from gapsense.services.guard_service import GuardService
    from gapsense.services.media_service import MediaService
    from gapsense.services.worker_service import WorkerService

    try:
        # Extract media info (URL for Twilio, ID for Meta)
        media_id = voice_content.get("url") or voice_content.get("id")
        mime_type = voice_content.get("mime_type", "audio/ogg")

        if not media_id:
            logger.warning(f"No media ID/URL in voice content: {voice_content}")
            return

        # Download audio from WhatsApp
        client = get_whatsapp_client()
        audio_bytes = await client.download_media(media_id=media_id)

        # Get parent's student
        stmt = (
            select(Student)
            .where(Student.primary_parent_id == parent.id)
            .order_by(Student.created_at.desc())  # type: ignore[attr-defined]
            .limit(1)
        )
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()

        if not student:
            # No students yet - prompt parent to complete onboarding
            await client.send_text_message(
                to=parent.phone,
                text="⚠️ Please complete registration first before sending voice messages.",
            )
            return

        # Initialize VoiceMicroCoaching with services
        ai_client = AsyncAIClient(anthropic_api_key=settings.ANTHROPIC_API_KEY)
        prompt_service = PromptService(settings=settings)
        guard_service = GuardService(ai_client=ai_client, prompt_service=prompt_service)
        media_service = MediaService(settings=settings)
        worker_service = WorkerService(ai_client=ai_client, media_service=media_service, guard_service=guard_service, prompt_service=prompt_service, settings=settings, db=db)

        coaching = VoiceMicroCoaching(
            db=db,
            ai_client=ai_client,
            prompt_service=prompt_service,
            guard_service=guard_service,
            media_service=media_service,
            worker_service=worker_service,
        )

        # Process voice message
        from gapsense.core.country_utils import get_country_from_parent

        result = await coaching.handle_voice_message(
            parent=parent,
            student=student,
            audio_bytes=audio_bytes,
            filename=f"voice_{media_id[:8]}.ogg",
            content_type=mime_type,
            country=get_country_from_parent(parent, student),
            language=parent.preferred_language or "en",
        )

        if result.success:
            logger.info(f"Voice coaching queued for parent {parent.phone}")
        else:
            logger.error(f"Voice coaching failed: {result.error}")
            await client.send_text_message(
                to=parent.phone,
                text=f"⚠️ Failed to process voice message: {result.error}",
            )

    except Exception as e:
        logger.error(f"Failed to handle parent voice: {e}", exc_info=True)
        # Send error message to parent
        try:
            client = get_whatsapp_client()
            await client.send_text_message(
                to=parent.phone,
                text="⚠️ Sorry, we encountered an error processing your voice message. Please try again.",
            )
        except Exception:
            pass  # Don't fail if error message fails
