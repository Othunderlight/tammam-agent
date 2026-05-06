import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx
from ai.tools.crm_context import get_api_key


class Platform(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"


@dataclass
class SessionSource:
    platform: Platform
    chat_id: str
    chat_name: Optional[str] = None
    chat_type: str = "dm"
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    thread_id: Optional[str] = None
    chat_topic: Optional[str] = None


class SessionStore:
    """Session manager using external API."""

    def __init__(self):
        self._base_url = os.getenv("SYSTEM_API_ENDPOINT")
        if not self._base_url:
            raise ValueError("SYSTEM_API_ENDPOINT not set")
        self._endpoint = (
            f"{self._base_url.rstrip('/')}/integrations/integration-sessions/"
        )

    def _generate_session_key(self, source: SessionSource) -> str:
        """Build session key from source."""
        platform = source.platform.value

        if source.chat_type == "dm":
            if source.chat_id:
                if source.thread_id:
                    return (
                        f"agent:main:{platform}:dm:{source.chat_id}:{source.thread_id}"
                    )
                return f"agent:main:{platform}:dm:{source.chat_id}"
            if source.thread_id:
                return f"agent:main:{platform}:dm:{source.thread_id}"
            return f"agent:main:{platform}:dm"

        key_parts = ["agent:main", platform, source.chat_type]
        if source.chat_id:
            key_parts.append(source.chat_id)
        if source.thread_id:
            key_parts.append(source.thread_id)
        return ":".join(key_parts)

    def _get_session(self, key: str) -> Optional[dict]:
        """GET session by key from API."""
        try:
            api_key = get_api_key()
            if not api_key:
                return None

            headers = {"Authorization": f"Api-Key {api_key}"}
            response = httpx.get(
                self._endpoint,
                params={"key": key, "latest": True},
                headers=headers,
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def _create_session(self, key: str, session_id: str) -> dict:
        """POST to create new session."""
        api_key = get_api_key()
        if not api_key:
            raise ValueError("API key not set in context")

        headers = {"Authorization": f"Api-Key {api_key}"}
        response = httpx.post(
            self._endpoint,
            json={"key": key, "session": session_id},
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    def get_or_create_session_id(self, source: SessionSource) -> str:
        """Get existing session_id or create new one."""
        key = self._generate_session_key(source)

        # Try to get existing session
        existing = self._get_session(key)
        if existing and existing.get("session"):
            return existing["session"]

        # Create new session
        session_id = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        self._create_session(key, session_id)

        return session_id

    def reset_session(self, source: SessionSource) -> str:
        """Reset session, creating new session_id."""
        key = self._generate_session_key(source)

        # Always create new session_id
        session_id = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        self._create_session(key, session_id)

        return session_id
