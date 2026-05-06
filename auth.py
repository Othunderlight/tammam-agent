import os
import time
from pathlib import Path
from typing import Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Path to keys
# In production/Docker, these will likely be in the current directory or specified via env
BASE_DIR = Path(__file__).resolve().parent
PRIVATE_KEY_PATH = os.getenv("JWT_PRIVATE_KEY_PATH", BASE_DIR / "jwt_private_key.pem")
PUBLIC_KEY_PATH = os.getenv("JWT_PUBLIC_KEY_PATH", BASE_DIR / "jwt_public_key.pem")
DJANGO_API_URL = os.getenv("SYSTEM_API_ENDPOINT")


security = HTTPBearer()


def get_public_key():
    with open(PUBLIC_KEY_PATH, "r") as f:
        return f.read()


def get_private_key():
    with open(PRIVATE_KEY_PATH, "r") as f:
        return f.read()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies the JWT token sent from the Frontend or Django.
    Also supports Django-generated API keys as a fallback by validating them against Django.
    """
    token = credentials.credentials

    # Try JWT token first
    try:
        public_key = get_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="your-api-audience",
            issuer="your-api-issuer",
        )
        payload["auth_method"] = "jwt"
        payload["token"] = token
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        pass  # Fall through to API key check

    # Try Django API key validation
    try:
        headers = {"Authorization": f"Api-Key {token}"}
        with httpx.Client() as client:
            response = client.get(f"{DJANGO_API_URL}/auth/user/", headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "user_id": str(user_data.get("id", "system")),
                    "auth_method": "api_key",
                    "api_key": token,
                    "user_data": user_data,
                }
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid token or API key")


def generate_system_token(user_id: str = None):
    """
    Generates a 'System' JWT token for FastAPI to authenticate with Django.

    Args:
        user_id: Optional user ID to impersonate. If not provided, defaults to system user.
    """
    private_key = get_private_key()
    now = int(time.time())
    payload = {
        "token_type": "access",
        "jti": os.urandom(16).hex(),
        "user_id": user_id or "1",  # Use provided user_id or fallback to admin
        "username": "system-ai" if not user_id else f"ai-for-{user_id}",
        "iat": now,
        "exp": now + 600,  # 10 minutes
        "aud": "your-api-audience",
        "iss": "your-api-issuer",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")
