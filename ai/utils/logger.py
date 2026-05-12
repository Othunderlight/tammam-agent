import json
import logging
import os
import queue
import threading
import traceback
import uuid
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

LOG_DIR = os.getenv("LOG_DIR", "logs")
TIMEOUT_SECONDS = 120
GOOGLE_SHEETS_LOG_URL = os.getenv("GOOGLE_SHEETS_LOG_URL")
GOOGLE_SHEETS_MAX_FIELD = int(os.getenv("GOOGLE_SHEETS_MAX_FIELD", "1000"))
CONV_LOGGER_WEBHOOK = os.getenv("CONV_LOGGER_WEBHOOK")
_sheets_queue: "queue.Queue[dict]" = queue.Queue()
_sheets_worker_started = False
_correlation_lock = threading.Lock()
_correlation_map: dict = {}
_pending_queries: dict = {}
_PENDING_TTL_SECONDS = 3600


def setup_conversation_logger() -> logging.Logger:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("conversation")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    handler = TimedRotatingFileHandler(
        f"{LOG_DIR}/conversations.json",
        when="midnight",
        interval=1,
        backupCount=30,
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    return logger


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            log_data = json.loads(record.getMessage())
        except json.JSONDecodeError:
            log_data = {"message": record.getMessage()}
        log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return json.dumps(log_data)


_conversation_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _conversation_logger
    if _conversation_logger is None:
        _conversation_logger = setup_conversation_logger()
    return _conversation_logger


def _truncate_value(value: Any, max_len: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _pick_inbound_message(inbound: dict) -> Optional[str]:
    if not inbound:
        return None
    for key in ("message_text", "user_msg", "message", "text"):
        if inbound.get(key):
            return inbound.get(key)
    return None


def _pick_timestamp(log_data: dict, timing: dict) -> Optional[str]:
    return log_data.get("timestamp") or timing.get("completed_at") or timing.get("started_at")


def _cleanup_pending(now_ts: float) -> None:
    expired = [k for k, v in _pending_queries.items() if now_ts - v.get("ts", now_ts) > _PENDING_TTL_SECONDS]
    for key in expired:
        _pending_queries.pop(key, None)


def _coerce_correlation_id(original_id: Optional[str]) -> str:
    with _correlation_lock:
        now_ts = datetime.utcnow().timestamp()
        _cleanup_pending(now_ts)
        if not original_id:
            new_id = str(uuid.uuid4())
            return new_id
        mapped = _correlation_map.get(original_id)
        if mapped:
            return mapped
        mapped = str(uuid.uuid4())
        _correlation_map[original_id] = mapped
        return mapped


def _pick_correlation_id(log_data: dict, timing: dict) -> Optional[str]:
    return _coerce_correlation_id(log_data.get("correlation_id"))


def _infer_status(log_data: dict, outbound: dict, inbound: dict) -> Optional[str]:
    status = log_data.get("status")
    if status:
        return status
    if outbound.get("messages"):
        return "outbound"
    if inbound:
        return "inbound"
    return None


def _flatten_log_for_sheet(log_data: dict) -> dict:
    user = log_data.get("user", {}) or {}
    inbound = log_data.get("inbound", {}) or {}
    outbound = log_data.get("outbound", {}) or {}
    timing = log_data.get("timing", {}) or {}

    flattened = {
        "timestamp": _pick_timestamp(log_data, timing),
        "correlation_id": _pick_correlation_id(log_data, timing),
        "channel": log_data.get("channel"),
        "message_type": log_data.get("message_type"),
        "status": _infer_status(log_data, outbound, inbound),
        "duration_seconds": timing.get("duration_seconds"),
        "user_id": user.get("user_id"),
        "email": user.get("email"),
        "first_name": user.get("first_name"),
        "organization_id": user.get("organization_id"),
        "organization_name": user.get("organization_name"),
        "inbound_message": _pick_inbound_message(inbound),
        "outbound_count": outbound.get("message_count"),
        "outbound_messages": json.dumps(outbound.get("messages", [])),
        "error_type": (log_data.get("error") or {}).get("error_type"),
        "error_message": (log_data.get("error") or {}).get("error_message"),
        "source": "fastai",
    }

    return {k: _truncate_value(v, GOOGLE_SHEETS_MAX_FIELD) for k, v in flattened.items()}


def _send_log_to_google_sheet(log_data: dict) -> None:
    if not GOOGLE_SHEETS_LOG_URL:
        return

    try:
        params = _flatten_log_for_sheet(log_data)
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            client.get(GOOGLE_SHEETS_LOG_URL, params=params)
    except Exception:
        # Never allow logging failures to impact app behavior.
        return


def _sheets_worker() -> None:
    while True:
        item = _sheets_queue.get()
        if item is None:
            return
        _send_log_to_google_sheet(item)
        _sheets_queue.task_done()


def _ensure_sheets_worker() -> None:
    global _sheets_worker_started
    if _sheets_worker_started:
        return
    _sheets_worker_started = True
    threading.Thread(target=_sheets_worker, daemon=True).start()


def _enqueue_google_sheet_log(log_data: dict) -> None:
    if not GOOGLE_SHEETS_LOG_URL:
        return
    _ensure_sheets_worker()
    _sheets_queue.put(log_data)


def log_conversation(data: dict):
    data["correlation_id"] = _coerce_correlation_id(data.get("correlation_id"))
    get_logger().info(json.dumps(data))
    _enqueue_google_sheet_log(data)
    _enqueue_conversation_webhook(data)


def _build_webhook_payload(log_data: dict) -> dict:
    user = log_data.get("user", {}) or {}
    inbound = log_data.get("inbound", {}) or {}
    outbound = log_data.get("outbound", {}) or {}
    timing = log_data.get("timing", {}) or {}

    query = _pick_inbound_message(inbound)
    messages = outbound.get("messages") or []
    result = messages[0] if messages else None

    status = _infer_status(log_data, outbound, inbound)
    correlation_id = log_data.get("correlation_id")

    if status == "inbound":
        return {
            "correlation_id": correlation_id,
            "user_name": user.get("first_name"),
            "email": user.get("email"),
            "query": query,
        }

    return {
        "correlation_id": correlation_id,
        "status": status,
        "duration_seconds": timing.get("duration_seconds"),
        "user_name": user.get("first_name"),
        "email": user.get("email"),
        "query": query,
        "result": result,
    }


def _send_conversation_webhook(log_data: dict) -> None:
    if not CONV_LOGGER_WEBHOOK:
        return
    try:
        payload = _build_webhook_payload(log_data)
        if payload.get("query"):
            with _correlation_lock:
                _pending_queries[payload.get("correlation_id")] = {
                    "query": payload.get("query"),
                    "ts": datetime.utcnow().timestamp(),
                }
        if payload.get("status") == "outbound" and not payload.get("query"):
            with _correlation_lock:
                pending = _pending_queries.pop(payload.get("correlation_id"), None)
                if pending:
                    payload["query"] = pending.get("query")
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            client.post(CONV_LOGGER_WEBHOOK, json=payload)
    except Exception:
        return


def _enqueue_conversation_webhook(log_data: dict) -> None:
    if not CONV_LOGGER_WEBHOOK:
        return
    threading.Thread(target=_send_conversation_webhook, args=(log_data,), daemon=True).start()


def extract_user_info(credentials: dict) -> dict:
    results = credentials.get("results", [])
    if not results:
        return {}

    user_data = results[0]
    user = user_data.get("user", {})
    org = user.get("organization", {})
    keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}

    # Combine user_id and email for better safety in production (e.g., 1+example+gmail+com)
    original_id = str(user.get("id"))
    email = user.get("email") or ""
    safe_email = email.replace("@", "+").replace(".", "+")
    combined_user_id = f"{original_id}+{safe_email}" if safe_email else original_id

    return {
        "user_id": combined_user_id,
        "email": email,
        "first_name": user.get("first_name"),
        "organization_id": org.get("id"),
    }


async def tracked_execution(
    correlation_id: str,
    channel: str,
    message_type: str,
    user_info: dict,
    inbound_message: str,
    func: Callable,
    *args,
    **kwargs,
) -> dict:
    correlation_id = str(uuid.uuid4())
    logger = get_logger()
    started_at = datetime.utcnow()
    outbound_messages = []
    status = "success"
    error_detail = None

    original_callback = kwargs.get("message_callback")
    wrapped_callback = None

    if original_callback:

        async def callback_wrapper(msg: str):
            outbound_messages.append(msg)
            await original_callback(msg)

        kwargs["message_callback"] = callback_wrapper

    try:
        result = await func(*args, **kwargs)

        if result and result.get("messages"):
            outbound_messages.extend(result.get("messages", []))

        return result

    except Exception as e:
        status = "error"
        error_detail = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
        }
        raise

    finally:
        completed_at = datetime.utcnow()
        duration_seconds = (completed_at - started_at).total_seconds()

        log_conversation(
            {
                "correlation_id": correlation_id,
                "channel": channel,
                "message_type": message_type,
                "user": {
                    "user_id": user_info.get("user_id"),
                    "first_name": user_info.get("first_name"),
                    "email": user_info.get("email"),
                    "organization_id": user_info.get("organization_id"),
                    "organization_name": user_info.get("organization_name"),
                },
                "inbound": {
                    "message_text": inbound_message[:1000] if inbound_message else None,
                },
                "outbound": {
                    "messages": [msg[:1000] for msg in outbound_messages],
                    "message_count": len(outbound_messages),
                },
                "timing": {
                    "started_at": started_at.isoformat() + "Z",
                    "completed_at": completed_at.isoformat() + "Z",
                    "duration_seconds": round(duration_seconds, 2),
                },
                "status": status,
                "error": error_detail,
            }
        )
