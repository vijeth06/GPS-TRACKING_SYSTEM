"""
Authentication Service
======================
Password hashing, JWT issuance, and user bootstrap logic.
"""

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError

from backend.database.connection import get_database


JWT_SECRET = os.getenv("JWT_SECRET", "gps-tracking-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))


class UserRole:
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


def _now() -> datetime:
    return datetime.utcnow()


class AuthService:
    def __init__(self):
        self.db = get_database()

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
        if not salt:
            salt = base64.b64encode(os.urandom(16)).decode("utf-8")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120000,
        )
        return {
            "password_salt": salt,
            "password_hash": base64.b64encode(digest).decode("utf-8"),
        }

    @staticmethod
    def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
        hashed = AuthService.hash_password(password, password_salt)["password_hash"]
        return hmac.compare_digest(hashed, password_hash)

    def create_access_token(self, user: Dict[str, Any]) -> str:
        expire = _now() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        payload = {
            "sub": user["username"],
            "role": user["role"],
            "exp": expire,
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def decode_token(self, token: str) -> Dict[str, Any]:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    async def ensure_default_admin(self) -> None:
        existing = await self.db.users.find_one({"username": "admin"})
        if existing:
            return

        pwd = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
        hash_obj = self.hash_password(pwd)
        await self.db.users.insert_one(
            {
                "username": "admin",
                "full_name": "System Admin",
                "role": UserRole.ADMIN,
                "is_active": True,
                **hash_obj,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = await self.db.users.find_one({"username": username, "is_active": True})
        if not user:
            return None

        if not self.verify_password(password, user["password_hash"], user["password_salt"]):
            return None

        return user

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return await self.db.users.find_one({"username": username, "is_active": True})

    @staticmethod
    def to_public_user(user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(user.get("_id", "")),
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "is_active": user.get("is_active", True),
        }
