"""
Webhook Adapter for Multi-Provider Support

Normalizes incoming webhooks from Meta and Twilio into a common format
so the webhook handler doesn't need to know which provider is active.
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger(__name__)


async def normalize_webhook(request: Request) -> dict[str, Any] | None:
    """Normalize webhook payload from any provider to Meta-compatible format.

    This allows the existing webhook handler to work unchanged regardless
    of which provider is sending the webhook.

    Args:
        request: FastAPI Request object

    Returns:
        Normalized payload in Meta webhook format, or None if unrecognized
    """
    content_type = request.headers.get("content-type", "")

    # Twilio sends form-encoded data
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        form_dict = dict(form_data)

        if "MessageSid" in form_dict:
            return _normalize_twilio_webhook(form_dict)

    # Meta sends JSON
    try:
        body = await request.json()
    except Exception:
        return None

    if isinstance(body, dict) and body.get("object") == "whatsapp_business_account":
        return body  # Already in Meta format

    # Return non-WhatsApp Meta webhooks (e.g., Instagram) so handler can ignore them
    if isinstance(body, dict) and body.get("object"):
        return body

    return None


def _normalize_twilio_webhook(data: dict[str, Any]) -> dict[str, Any]:
    """Convert Twilio webhook format to Meta-compatible format.

    Twilio format:
        From: whatsapp:+233244123456
        Body: Hello
        MessageSid: SMxxxxx
        NumMedia: 0
        MediaUrl0: https://...
        MediaContentType0: image/jpeg

    Meta format (output):
        {
            "object": "whatsapp_business_account",
            "entry": [{"changes": [{"field": "messages", "value": {...}}]}]
        }
    """
    from_number = data.get("From", "")
    body = data.get("Body", "")
    message_sid = data.get("MessageSid", "unknown")
    num_media = int(data.get("NumMedia", "0"))

    # Strip whatsapp: prefix and normalize to E.164
    phone = from_number.replace("whatsapp:", "").strip()
    if phone and not phone.startswith("+"):
        phone = f"+{phone}"

    # Determine message type and build message object
    message: dict[str, Any] = {
        "from": phone,
        "id": message_sid,
        "timestamp": str(int(time.time())),
    }

    if num_media > 0:
        media_url = data.get("MediaUrl0", "")
        media_type = data.get("MediaContentType0", "")

        if media_type.startswith("image/"):
            message["type"] = "image"
            message["image"] = {
                "id": message_sid,
                "mime_type": media_type,
                "url": media_url,
            }
        elif media_type.startswith("audio/"):
            message["type"] = "voice"
            message["voice"] = {
                "id": message_sid,
                "mime_type": media_type,
                "url": media_url,
            }
        else:
            message["type"] = "document"
            message["document"] = {
                "id": message_sid,
                "mime_type": media_type,
                "url": media_url,
            }
    elif body:
        # Check if this is a numbered reply to a button/list fallback
        button_reply = _detect_numbered_reply(body)
        if button_reply:
            message["type"] = "interactive"
            message["interactive"] = {
                "type": "button_reply",
                "button_reply": button_reply,
            }
        else:
            message["type"] = "text"
            message["text"] = {"body": body}
    else:
        message["type"] = "text"
        message["text"] = {"body": ""}

    # Build Meta-compatible structure
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": data.get("To", ""),
                                "phone_number_id": "twilio",
                            },
                            "messages": [message],
                        },
                    }
                ]
            }
        ],
    }


def _detect_numbered_reply(body: str) -> dict[str, str] | None:
    """Detect if a text message is a numbered reply to a button/list fallback.

    When Twilio sends buttons as numbered lists, users reply with "1", "2", etc.
    We convert these back to button_reply format for the flow executor.

    Args:
        body: Message body text

    Returns:
        Button reply dict if detected, None otherwise
    """
    stripped = body.strip()

    # Only match single numbers 1-10
    if re.match(r"^[1-9]$|^10$", stripped):
        return {
            "id": f"numbered_reply_{stripped}",
            "title": stripped,
        }

    return None
