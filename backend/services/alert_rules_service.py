"""
Alert Rules Service
===================
Implements alert lifecycle rules such as cooldown/debouncing.
"""

from datetime import datetime, timedelta

from backend.database.connection import get_database


class AlertRulesService:
    def __init__(self):
        self.db = get_database()

    async def should_emit_alert(self, device_id: str, alert_type: str, cooldown_seconds: int = 120) -> bool:
        """Return False if alert is still in cooldown window."""
        now = datetime.utcnow()
        key = f"{device_id}:{alert_type}"
        state = await self.db.alert_rule_state.find_one({"key": key})
        if state and state.get("last_emitted_at"):
            delta = now - state["last_emitted_at"]
            if delta < timedelta(seconds=cooldown_seconds):
                return False

        await self.db.alert_rule_state.update_one(
            {"key": key},
            {
                "$set": {
                    "device_id": device_id,
                    "alert_type": alert_type,
                    "last_emitted_at": now,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return True
