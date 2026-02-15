"""
WhatsApp Cloud API Webhook Handlers

Handles webhook verification (GET) and incoming messages (POST).
Based on Meta WhatsApp Cloud API v21.0 specification.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response

from gapsense.config import settings

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
async def handle_webhook(request: Request) -> dict[str, str]:
    """Handle incoming WhatsApp messages and status updates.

    WhatsApp Cloud API sends POST requests with:
    - Inbound messages (text, image, voice, button, list)
    - Delivery statuses (sent, delivered, read, failed)
    - Read receipts

    Returns:
        Always returns {"status": "received"} or {"status": "ignored"}
        to prevent Meta from retrying

    Note:
        This endpoint must respond within 20 seconds or Meta will retry.
        Complex processing should be offloaded to async queues (SQS).
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning(f"Failed to parse webhook body: {e}")
        # Still return 200 to prevent Meta retries
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
                await _handle_message(message, value)

            # Handle status updates (delivered, read, failed)
            statuses = value.get("statuses", [])
            for status in statuses:
                await _handle_status_update(status)

    return {"status": "received"}


async def _handle_message(message: dict[str, Any], value: dict[str, Any]) -> None:
    """Handle an inbound WhatsApp message.

    Args:
        message: Message object from webhook
        value: Parent value object with metadata

    Note:
        For MVP Week 1, this is a placeholder that logs the message.
        Full implementation will:
        1. Identify/create parent by phone number
        2. Update conversation state
        3. Route to appropriate flow handler
        4. Send response via WhatsApp client
    """
    message_type = message.get("type")
    from_number = message.get("from")
    message_id = message.get("id")

    logger.info(f"Received {message_type} message from {from_number} (ID: {message_id})")

    # Extract message content based on type
    content = _extract_message_content(message)

    logger.debug(f"Message content: {content}")

    # TODO: Week 1 Implementation
    # 1. Get or create Parent by phone number
    # 2. Check conversation_state
    # 3. Route to FlowExecutor
    # 4. Generate response
    # 5. Send via WhatsAppClient


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
