"""Notification service with provider integrations for webhook, email, and SMS."""

import asyncio
from datetime import datetime
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, Any, List

from bson import ObjectId
import httpx

from backend.database.connection import get_database


class NotificationService:
    def __init__(self):
        self.db = get_database()

    async def list_channels(self) -> List[Dict[str, Any]]:
        rows = await self.db.notification_channels.find({}).sort("updated_at", -1).to_list(length=200)
        return [self._to_channel_response(row) for row in rows]

    async def upsert_channel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        existing = await self.db.notification_channels.find_one(
            {"name": payload["name"], "channel_type": payload["channel_type"]}
        )
        if existing:
            await self.db.notification_channels.update_one(
                {"_id": existing["_id"]},
                {"$set": {**payload, "updated_at": now}},
            )
            existing.update(payload)
            existing["updated_at"] = now
            return self._to_channel_response(existing)

        doc = {**payload, "created_at": now, "updated_at": now}
        result = await self.db.notification_channels.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_channel_response(doc)

    async def delete_channel(self, channel_id: str) -> bool:
        try:
            result = await self.db.notification_channels.delete_one({"_id": ObjectId(channel_id)})
        except Exception:
            return False
        return result.deleted_count > 0

    async def send_test(self, channel_id: str, message: str, severity: str) -> Dict[str, Any]:
        channel = await self._get_channel(channel_id)
        if not channel:
            return {
                "delivered": False,
                "provider": "unknown",
                "details": "Channel not found",
                "dispatched_at": datetime.utcnow(),
            }
        return await self._dispatch(channel, message, severity, metadata={"test": True})

    async def notify_alert_event(self, alert: Dict[str, Any], event_name: str) -> List[Dict[str, Any]]:
        severity = (alert.get("severity") or "medium").lower()
        channels = await self.db.notification_channels.find(
            {"enabled": True, "severity_filter": {"$in": [severity]}}
        ).to_list(length=200)

        message = f"[{event_name}] {alert.get('device_id')} - {alert.get('message')}"
        outcomes = []
        for channel in channels:
            outcome = await self._dispatch(channel, message, severity, metadata={"alert_id": alert.get("id")})
            outcomes.append(outcome)
        return outcomes

    async def _get_channel(self, channel_id: str):
        try:
            return await self.db.notification_channels.find_one({"_id": ObjectId(channel_id)})
        except Exception:
            return None

    async def _dispatch(self, channel: Dict[str, Any], message: str, severity: str, metadata: Dict[str, Any]):
        now = datetime.utcnow()
        provider = (channel.get("channel_type") or "in_app").lower()

        if not channel.get("enabled", True):
            delivered = False
            details = "Channel disabled"
        elif provider in ["slack", "webhook"]:
            delivered, details = await self._send_webhook(channel, message, severity)
        elif provider in ["email", "smtp"]:
            delivered, details = await self._send_email(channel, message, severity)
        elif provider in ["sms", "twilio"]:
            delivered, details = await self._send_sms(channel, message, severity)
        elif provider == "in_app":
            delivered, details = True, "Stored as in-app event"
        else:
            delivered, details = False, f"Unsupported channel type: {provider}"

        event_doc = {
            "channel_id": str(channel.get("_id")),
            "channel_name": channel.get("name"),
            "provider": provider,
            "severity": severity,
            "message": message,
            "delivered": delivered,
            "details": details,
            "metadata": metadata,
            "created_at": now,
        }
        await self.db.notification_events.insert_one(event_doc)

        return {
            "delivered": delivered,
            "provider": provider,
            "details": details,
            "dispatched_at": now,
        }

    async def _send_webhook(self, channel: Dict[str, Any], message: str, severity: str) -> tuple[bool, str]:
        url = channel.get("webhook_url") or os.getenv("NOTIFICATION_WEBHOOK_URL", "")
        if not url:
            return False, "Missing webhook_url"

        payload = {
            "text": message,
            "severity": severity,
            "channel": channel.get("name"),
            "sent_at": datetime.utcnow().isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
            if 200 <= response.status_code < 300:
                return True, f"Webhook delivered ({response.status_code})"
            return False, f"Webhook failed ({response.status_code})"
        except Exception as exc:
            return False, f"Webhook error: {str(exc)}"

    async def _send_email(self, channel: Dict[str, Any], message: str, severity: str) -> tuple[bool, str]:
        recipient = channel.get("recipient") or os.getenv("NOTIFICATION_EMAIL_RECIPIENT", "")
        host = os.getenv("SMTP_HOST", "")
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("SMTP_FROM", user)
        port = int(os.getenv("SMTP_PORT", "587"))
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() not in ["0", "false", "no"]

        if not recipient:
            return False, "Missing email recipient"
        if not host:
            return False, "Missing SMTP_HOST"

        subject = f"[GPS Alert:{severity.upper()}] {channel.get('name')}"
        body = f"{message}\n\nSeverity: {severity}\nSent at: {datetime.utcnow().isoformat()}"

        def _send():
            email = EmailMessage()
            email["Subject"] = subject
            email["From"] = from_addr
            email["To"] = recipient
            email.set_content(body)

            if use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.starttls(context=context)
                    if user and password:
                        server.login(user, password)
                    server.send_message(email)
            else:
                with smtplib.SMTP_SSL(host, port, timeout=10) as server:
                    if user and password:
                        server.login(user, password)
                    server.send_message(email)

        try:
            await asyncio.to_thread(_send)
            return True, f"Email sent to {recipient}"
        except Exception as exc:
            return False, f"Email error: {str(exc)}"

    async def _send_sms(self, channel: Dict[str, Any], message: str, severity: str) -> tuple[bool, str]:
        to_number = channel.get("recipient") or os.getenv("SMS_TO", "")
        from_number = os.getenv("TWILIO_FROM_NUMBER", "")
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

        if not to_number:
            return False, "Missing SMS recipient"
        if not (from_number and account_sid and auth_token):
            return False, "Missing Twilio credentials"

        body = f"[{severity.upper()}] {message}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    data={"From": from_number, "To": to_number, "Body": body},
                    auth=(account_sid, auth_token),
                )
            if 200 <= response.status_code < 300:
                return True, f"SMS sent to {to_number}"
            return False, f"SMS failed ({response.status_code})"
        except Exception as exc:
            return False, f"SMS error: {str(exc)}"

    @staticmethod
    def _to_channel_response(doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "channel_type": doc.get("channel_type"),
            "name": doc.get("name"),
            "enabled": doc.get("enabled", True),
            "recipient": doc.get("recipient"),
            "webhook_url": doc.get("webhook_url"),
            "severity_filter": doc.get("severity_filter", ["medium", "high", "critical"]),
            "created_at": doc.get("created_at", datetime.utcnow()),
            "updated_at": doc.get("updated_at", datetime.utcnow()),
        }
