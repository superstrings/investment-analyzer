"""
DingTalk notification service.

Sends messages to DingTalk group via custom robot webhook.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from typing import Optional

import requests

from config import settings
from db.database import get_session
from db.models import NotificationLog

logger = logging.getLogger(__name__)


class DingtalkService:
    """Service for sending DingTalk messages."""

    def __init__(
        self,
        webhook_url: str = None,
        secret: str = None,
    ):
        self.webhook_url = webhook_url or settings.dingtalk.webhook_url
        self.secret = secret or settings.dingtalk.secret

    def _sign(self, timestamp: str) -> str:
        """Generate HMAC-SHA256 signature for DingTalk."""
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return urllib.parse.quote_plus(base64.b64encode(hmac_code))

    def _get_signed_url(self) -> str:
        """Get webhook URL with timestamp and signature."""
        timestamp = str(round(time.time() * 1000))
        sign = self._sign(timestamp)
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def send_text(
        self,
        content: str,
        user_id: int = None,
        message_type: str = "report",
    ) -> bool:
        """Send a text message to DingTalk."""
        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }
        return self._send(payload, content[:200], user_id, message_type)

    def send_markdown(
        self,
        title: str,
        text: str,
        user_id: int = None,
        message_type: str = "report",
    ) -> bool:
        """Send a markdown message to DingTalk."""
        payload = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
        }
        return self._send(payload, title, user_id, message_type)

    def _send(
        self,
        payload: dict,
        summary: str,
        user_id: int = None,
        message_type: str = "report",
    ) -> bool:
        """Send a message payload to DingTalk and log it."""
        if not self.webhook_url:
            logger.warning("DingTalk webhook URL not configured")
            return False

        try:
            url = self._get_signed_url() if self.secret else self.webhook_url
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()

            result = response.json()
            success = result.get("errcode", -1) == 0

            self._log_notification(
                user_id=user_id,
                message_type=message_type,
                summary=summary,
                status="sent" if success else "failed",
                error=result.get("errmsg") if not success else None,
            )

            if not success:
                logger.error(f"DingTalk API error: {result}")

            return success

        except Exception as e:
            logger.error(f"DingTalk send failed: {e}")
            self._log_notification(
                user_id=user_id,
                message_type=message_type,
                summary=summary,
                status="failed",
                error=str(e),
            )
            return False

    def _log_notification(
        self,
        user_id: int = None,
        message_type: str = "report",
        summary: str = "",
        status: str = "sent",
        error: str = None,
    ) -> None:
        """Log notification to database."""
        try:
            with get_session() as session:
                log = NotificationLog(
                    user_id=user_id,
                    channel="dingtalk",
                    message_type=message_type,
                    content_summary=summary[:500] if summary else None,
                    status=status,
                    error_message=error,
                )
                session.add(log)
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")


def create_dingtalk_service() -> DingtalkService:
    """Factory function for DingtalkService."""
    return DingtalkService()
