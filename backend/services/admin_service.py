"""User and team administration service."""

from datetime import datetime
from typing import Dict, Any, List, Optional

from bson import ObjectId

from backend.database.connection import get_database
from backend.services.auth_service import AuthService


class AdminService:
    def __init__(self):
        self.db = get_database()
        self.auth = AuthService()

    async def list_users(self) -> List[Dict[str, Any]]:
        rows = await self.db.users.find({}).sort("username", 1).to_list(length=500)
        return [self._public_user(r) for r in rows]

    async def create_user(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        hashed = self.auth.hash_password(payload["password"])
        doc = {
            "username": payload["username"],
            "full_name": payload.get("full_name"),
            "role": payload.get("role", "viewer"),
            "is_active": payload.get("is_active", True),
            **hashed,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.db.users.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._public_user(doc)

    async def update_user(self, username: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates = {}
        for key in ["full_name", "role", "is_active"]:
            if payload.get(key) is not None:
                updates[key] = payload.get(key)
        if not updates:
            row = await self.db.users.find_one({"username": username})
            return self._public_user(row) if row else None

        updates["updated_at"] = datetime.utcnow()
        await self.db.users.update_one({"username": username}, {"$set": updates})
        row = await self.db.users.find_one({"username": username})
        return self._public_user(row) if row else None

    async def list_teams(self) -> List[Dict[str, Any]]:
        rows = await self.db.teams.find({}).sort("team_name", 1).to_list(length=300)
        return [self._team_response(r) for r in rows]

    async def create_team(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        doc = {**payload, "created_at": now, "updated_at": now}
        result = await self.db.teams.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._team_response(doc)

    async def delete_team(self, team_id: str) -> bool:
        try:
            result = await self.db.teams.delete_one({"_id": ObjectId(team_id)})
        except Exception:
            return False
        return result.deleted_count > 0

    @staticmethod
    def _public_user(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row.get("_id", "")),
            "username": row.get("username"),
            "full_name": row.get("full_name"),
            "role": row.get("role"),
            "is_active": row.get("is_active", True),
        }

    @staticmethod
    def _team_response(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(row.get("_id", "")),
            "team_name": row.get("team_name"),
            "lead_username": row.get("lead_username"),
            "members": row.get("members", []),
            "on_call": row.get("on_call", False),
            "created_at": row.get("created_at", datetime.utcnow()),
            "updated_at": row.get("updated_at", datetime.utcnow()),
        }
