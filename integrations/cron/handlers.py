import asyncio
import os
from datetime import datetime
from typing import Optional

from ai.runs.integration_handler import handle_integration_message
from ai.runs.one_action import get_user_facing_error_message
from ai.runs.session_manager import Platform, SessionSource, SessionStore
from ai.tools.manage_api_key import clear_api_key, set_api_key
from ai.utils.logger import log_conversation, extract_user_info

from integrations.cron.credentials import (
    get_credentials_by_user_id,
    validate_credentials,
)
from integrations.cron.utils import update_cron_status, can_run_cron

session_store = SessionStore()

def build_cron_session_source(user_id: str, cron_id: str) -> SessionSource:
    """Build the session source for the Cron job."""
    return SessionSource(
        platform=Platform.CRON,
        chat_id=str(cron_id),
        user_id=str(user_id),
        chat_type="dm",
    )

# def get_cron_session_id(user_id: str, cron_id: int) -> str:
#     """Get or create session ID for Cron conversation."""
#     return session_store.get_or_create_session_id(build_cron_session_source(user_id, cron_id))

async def handle_cron_job(
    cron_id: str,
    user_id: int,
    prompt: str,
    no_agent: bool = False,
    deliver: str = "pass"
):

    """
    Handle a cron job triggered from Django.
    """
    # 1. Fetch Credentials
    credentials = await get_credentials_by_user_id(user_id)
    is_valid, error = validate_credentials(credentials)

    if not is_valid:
        return {"status": "failed", "error": f"Invalid credentials: {error}"}

    if not can_run_cron(credentials):
        return {"status": "failed", "error": "Credit limit reached"}

    user_info = extract_user_info(credentials)

    # 2. Set API Key
    results = credentials.get("results", [])
    user_data = results[0]
    keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}
    crm_api_key = keys.get("crm_api_key")
    if crm_api_key:
        set_api_key(crm_api_key)

    # 3. Execution
    started_at = datetime.utcnow()
    log_conversation({
        "channel": "cron",
        "message_type": "txt",
        "user": user_info,
        "inbound": {"prompt": prompt[:1000], "cron_id": cron_id},
        "timing": {"started_at": started_at.isoformat() + "Z"},
    })

    collected_messages = []

    async def message_callback(msg: str):
        collected_messages.append(msg)

    # Always create a fresh session for cron jobs to avoid history carryover
    session_id = session_store.reset_session(build_cron_session_source(user_id, cron_id))

    try:
        if no_agent:
            # Simulate agent success
            mock_msg = "greate, i have done it"
            await message_callback(mock_msg)
            result = {"status": "success", "answer": mock_msg}
            print(f"Cron {cron_id}: Simulating agent success (no_agent=True)")
        else:
            result = await handle_integration_message(
                prompt,
                credentials,
                message_callback=message_callback,
                session_id=session_id,
            )

        if result.get("status") == "success":
            # Handle delivery (placeholder)
            if deliver == "pass":
                pass

            return {"status": "success", "result": result}
        else:
            return {
                "status": "failed",
                "error": result.get("answer") or result.get("error") or "Unknown error"
            }

    except Exception as e:
        print(f"Cron handler error for job {cron_id}: {e}")
        return {
            "status": "failed",
            "error": get_user_facing_error_message(e)
        }
    finally:
        clear_api_key()

        completed_at = datetime.utcnow()
        duration_seconds = (completed_at - started_at).total_seconds()
        log_conversation({
            "channel": "cron",
            "message_type": "txt",
            "user": user_info,
            "outbound": {
                "messages": [msg[:500] for msg in collected_messages],
                "message_count": len(collected_messages),
            },
            "timing": {
                "started_at": started_at.isoformat() + "Z",
                "completed_at": completed_at.isoformat() + "Z",
                "duration_seconds": round(duration_seconds, 2),
            },
        })
