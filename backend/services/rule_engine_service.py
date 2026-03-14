"""Lightweight rule engine service for event-based automation."""

from datetime import datetime
from typing import Dict, Any, List

from bson import ObjectId

from backend.database.connection import get_database


class RuleEngineService:
    def __init__(self):
        self.db = get_database()

    async def list_rules(self) -> List[Dict[str, Any]]:
        rows = await self.db.rule_engine_rules.find({}).sort("priority", 1).to_list(length=300)
        return [self._to_response(row) for row in rows]

    async def create_rule(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        doc = {**payload, "created_at": now, "updated_at": now}
        result = await self.db.rule_engine_rules.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_response(doc)

    async def update_rule(self, rule_id: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        now = datetime.utcnow()
        try:
            await self.db.rule_engine_rules.update_one(
                {"_id": ObjectId(rule_id)},
                {"$set": {**payload, "updated_at": now}},
            )
            row = await self.db.rule_engine_rules.find_one({"_id": ObjectId(rule_id)})
        except Exception:
            return None
        return self._to_response(row) if row else None

    async def delete_rule(self, rule_id: str) -> bool:
        try:
            result = await self.db.rule_engine_rules.delete_one({"_id": ObjectId(rule_id)})
        except Exception:
            return False
        return result.deleted_count > 0

    async def evaluate_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        rules = await self.db.rule_engine_rules.find({"event_type": event_type, "enabled": True}).sort("priority", 1).to_list(length=200)
        matched: List[str] = []
        executed_actions: List[str] = []

        for rule in rules:
            if self._matches_conditions(rule.get("conditions", []), payload):
                matched.append(str(rule["_id"]))
                for action in rule.get("actions", []):
                    executed_actions.append(action.get("action_type", "unknown"))

        return {
            "matched_rule_ids": matched,
            "executed_actions": executed_actions,
        }

    @staticmethod
    def _matches_conditions(conditions: List[Dict[str, Any]], payload: Dict[str, Any]) -> bool:
        for cond in conditions:
            field = cond.get("field")
            op = cond.get("op")
            expected = cond.get("value")
            actual = payload.get(field)

            if op == "eq" and str(actual) != str(expected):
                return False
            if op == "neq" and str(actual) == str(expected):
                return False
            if op == "contains" and str(expected) not in str(actual):
                return False
            if op == "gt":
                try:
                    if float(actual) <= float(expected):
                        return False
                except Exception:
                    return False
            if op == "lt":
                try:
                    if float(actual) >= float(expected):
                        return False
                except Exception:
                    return False

        return True

    @staticmethod
    def _to_response(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row["_id"]),
            "name": row.get("name"),
            "description": row.get("description"),
            "event_type": row.get("event_type"),
            "enabled": row.get("enabled", True),
            "priority": row.get("priority", 100),
            "conditions": row.get("conditions", []),
            "actions": row.get("actions", []),
            "created_at": row.get("created_at", datetime.utcnow()),
            "updated_at": row.get("updated_at", datetime.utcnow()),
        }
