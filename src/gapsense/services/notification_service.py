"""
NotificationService Interface

Abstracts notification delivery (WhatsApp, demo logging, email, SMS, etc.)
to decouple business logic from delivery mechanism.

This allows:
- ExerciseBookScanner to work without WhatsApp dependency
- Demo/test environments to run without real WhatsApp API
- Future expansion to email, SMS, push notifications
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class NotificationService(ABC):
    """Abstract notification service interface."""

    @abstractmethod
    async def send_analysis_started(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Notify teacher that analysis has started.

        Args:
            teacher_phone: Teacher's phone number
            student_name: Name of student being analyzed
            country: Country code (for localization)
            language: Language code (for localization)

        Returns:
            True if notification sent successfully, False otherwise
        """

    @abstractmethod
    async def send_analysis_complete(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        dashboard_url: str | None = None,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Notify teacher that analysis is complete.

        Args:
            teacher_phone: Teacher's phone number
            student_name: Name of student analyzed
            dashboard_url: Optional URL to view results
            country: Country code (for localization)
            language: Language code (for localization)

        Returns:
            True if notification sent successfully, False otherwise
        """

    @abstractmethod
    async def send_analysis_failed(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        error_message: str,
        retry_count: int = 0,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Notify teacher that analysis failed.

        Args:
            teacher_phone: Teacher's phone number
            student_name: Name of student
            error_message: Human-readable error message
            retry_count: Number of retries attempted (0 = first attempt)
            country: Country code (for localization)
            language: Language code (for localization)

        Returns:
            True if notification sent successfully, False otherwise
        """

    @abstractmethod
    async def send_image_upload_acknowledged(
        self,
        *,
        teacher_phone: str,
        message: str,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Send immediate acknowledgment of image upload.

        Args:
            teacher_phone: Teacher's phone number
            message: Acknowledgment message
            country: Country code (for localization)
            language: Language code (for localization)

        Returns:
            True if notification sent successfully, False otherwise
        """


class WhatsAppNotificationService(NotificationService):
    """Production notification service using WhatsApp."""

    def __init__(self, whatsapp_client: Any) -> None:
        """Initialize with WhatsApp client.

        Args:
            whatsapp_client: WhatsAppClient instance
        """
        self.whatsapp = whatsapp_client

    async def send_analysis_started(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Send WhatsApp message that analysis started."""
        try:
            # TODO: Localize message based on country/language
            message = f"📸 Analysis started for {student_name}. I'll notify you when complete (usually 10-30 seconds)."

            await self.whatsapp.send_text_message(
                to=teacher_phone,
                text=message,
            )
            logger.info(
                "notification_sent",
                type="analysis_started",
                teacher_phone=teacher_phone,
                student_name=student_name,
            )
            return True
        except Exception as exc:
            logger.error(
                "notification_failed",
                type="analysis_started",
                teacher_phone=teacher_phone,
                error=str(exc),
            )
            return False

    async def send_analysis_complete(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        dashboard_url: str | None = None,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Send WhatsApp message that analysis is complete."""
        try:
            # TODO: Localize message based on country/language
            if dashboard_url:
                message = (
                    f"✅ Analysis complete for {student_name}!\n\n📊 View results: {dashboard_url}"
                )
            else:
                message = f"✅ Analysis complete for {student_name}! Results are being processed."

            await self.whatsapp.send_text_message(
                to=teacher_phone,
                text=message,
            )
            logger.info(
                "notification_sent",
                type="analysis_complete",
                teacher_phone=teacher_phone,
                student_name=student_name,
            )
            return True
        except Exception as exc:
            logger.error(
                "notification_failed",
                type="analysis_complete",
                teacher_phone=teacher_phone,
                error=str(exc),
            )
            return False

    async def send_analysis_failed(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        error_message: str,
        retry_count: int = 0,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Send WhatsApp message that analysis failed."""
        try:
            # TODO: Localize message based on country/language
            if retry_count > 0:
                message = (
                    f"⚠️ Analysis for {student_name} failed (retry {retry_count}/3). Retrying..."
                )
            else:
                message = f"❌ Analysis for {student_name} failed: {error_message}\n\nPlease try uploading again."

            await self.whatsapp.send_text_message(
                to=teacher_phone,
                text=message,
            )
            logger.info(
                "notification_sent",
                type="analysis_failed",
                teacher_phone=teacher_phone,
                student_name=student_name,
                retry_count=retry_count,
            )
            return True
        except Exception as exc:
            logger.error(
                "notification_failed",
                type="analysis_failed",
                teacher_phone=teacher_phone,
                error=str(exc),
            )
            return False

    async def send_image_upload_acknowledged(
        self,
        *,
        teacher_phone: str,
        message: str,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Send WhatsApp acknowledgment of image upload."""
        try:
            await self.whatsapp.send_text_message(
                to=teacher_phone,
                text=message,
            )
            logger.info(
                "notification_sent",
                type="upload_acknowledged",
                teacher_phone=teacher_phone,
            )
            return True
        except Exception as exc:
            logger.error(
                "notification_failed",
                type="upload_acknowledged",
                teacher_phone=teacher_phone,
                error=str(exc),
            )
            return False


class DemoNotificationService(NotificationService):
    """Demo/test notification service that only logs (no actual delivery)."""

    def __init__(self) -> None:
        """Initialize demo notification service."""
        self.notifications: list[dict[str, Any]] = []

    async def send_analysis_started(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Log analysis started (demo mode)."""
        notification = {
            "type": "analysis_started",
            "teacher_phone": teacher_phone,
            "student_name": student_name,
            "country": country,
            "language": language,
        }
        self.notifications.append(notification)
        logger.info(
            "demo_notification",
            **notification,
        )
        return True

    async def send_analysis_complete(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        dashboard_url: str | None = None,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Log analysis complete (demo mode)."""
        notification = {
            "type": "analysis_complete",
            "teacher_phone": teacher_phone,
            "student_name": student_name,
            "dashboard_url": dashboard_url,
            "country": country,
            "language": language,
        }
        self.notifications.append(notification)
        logger.info(
            "demo_notification",
            **notification,
        )
        return True

    async def send_analysis_failed(
        self,
        *,
        teacher_phone: str,
        student_name: str,
        error_message: str,
        retry_count: int = 0,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Log analysis failed (demo mode)."""
        notification = {
            "type": "analysis_failed",
            "teacher_phone": teacher_phone,
            "student_name": student_name,
            "error_message": error_message,
            "retry_count": retry_count,
            "country": country,
            "language": language,
        }
        self.notifications.append(notification)
        logger.info(
            "demo_notification",
            **notification,
        )
        return True

    async def send_image_upload_acknowledged(
        self,
        *,
        teacher_phone: str,
        message: str,
        country: str = "GH",
        language: str = "en",
    ) -> bool:
        """Log upload acknowledgment (demo mode)."""
        notification = {
            "type": "upload_acknowledged",
            "teacher_phone": teacher_phone,
            "message": message,
            "country": country,
            "language": language,
        }
        self.notifications.append(notification)
        logger.info(
            "demo_notification",
            **notification,
        )
        return True

    def get_notifications(self) -> list[dict[str, Any]]:
        """Get all captured notifications (for testing/inspection)."""
        return self.notifications

    def clear_notifications(self) -> None:
        """Clear notification history."""
        self.notifications.clear()
