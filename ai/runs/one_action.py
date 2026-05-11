import asyncio
import os
import re
import uuid
from typing import Optional

from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService
from google.adk.plugins import ReflectAndRetryToolPlugin
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, VertexAiSessionService
from google.genai import types
from pydantic import BaseModel

from ai.runs.stop_registry import register_active_run, unregister_active_run
from ai.utils.logging_plugin_full import FullLoggingPlugin
from ai.workflows.g_adk.manager.agent import create_agent

GOOGLE_CLOUD_PROJECT_NAME = os.getenv("GOOGLE_CLOUD_PROJECT_NAME")
GOOGLE_CLOUD_PROJECT_LOCATION = os.getenv("GOOGLE_CLOUD_PROJECT_LOCATION", "global")
GOOGLE_CLOUD_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
GOOGLE_CLOUD_AGENT_ENGINE_ID = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")

# Use Project Name (string ID) if available, otherwise fallback to Project ID (number)
GCP_PROJECT = GOOGLE_CLOUD_PROJECT_NAME or GOOGLE_CLOUD_PROJECT_ID
REASONING_ENGINE_APP_NAME = f"projects/{GCP_PROJECT}/locations/{GOOGLE_CLOUD_PROJECT_LOCATION}/reasoningEngines/{GOOGLE_CLOUD_AGENT_ENGINE_ID}"

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds
HIGH_DEMAND_MESSAGE = (
    "The agent is currently experiencing high demand. "
    "Spikes in demand are usually temporary. Please try again in a moment."
)

# Error substrings that indicate a transient/retryable failure
_RETRYABLE_PATTERNS = [
    "ServiceUnavailableError",
    "over capacity",
    "RateLimitError",
    "rate_limit",
    "Too Many Requests",
    "timeout",
    "Timeout",
    "ConnectionError",
    "APIConnectionError",
]

_HIGH_DEMAND_PATTERNS = [
    "currently experiencing high demand",
    '"status": "UNAVAILABLE"',
    '"code": 503',
]

_MCP_TOOL_FAILURE_PATTERNS = [
    "Failed to create MCP session",
    "Failed to get tools from toolset",
    "Failed to get tools from MCP server",
    "CRM tool server unavailable",
    "Tool server unavailable",
    "unhandled errors in a TaskGroup",
]

_TOOL_NOT_FOUND_PATTERN = re.compile(r"^Tool '.*' not found\.$", re.MULTILINE)


def _is_retryable(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    error_str = str(error)
    return any(pattern in error_str for pattern in _RETRYABLE_PATTERNS)


def get_user_facing_error_message(error: Exception) -> str:
    """Return a user-safe message for known agent failures."""
    error_str = str(error)

    if any(pattern in error_str for pattern in _HIGH_DEMAND_PATTERNS):
        return HIGH_DEMAND_MESSAGE

    if any(pattern in error_str for pattern in _MCP_TOOL_FAILURE_PATTERNS):
        return (
            "The CRM tools are currently unavailable, so I could not verify or"
            " complete that action. Please try again in a moment."
        )

    return "Sorry, something went wrong on my end. Please try again in a moment. 🙏"


class AgentRequest(BaseModel):
    user_id: str
    query: str
    crm_config: Optional[dict] = None
    user_preferences: Optional[dict] = None
    session_id: Optional[str] = None
    stop_key: Optional[str] = None
    api_keys: Optional[dict] = None


def _normalize_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None

    cleaned = text.strip()
    if not cleaned:
        return None

    return cleaned


def _extract_tool_runtime_error(error: Exception) -> Optional[str]:
    """Extract the dynamic tool-not-found details from an ADK exception."""
    error_str = str(error)
    lines = [line.strip() for line in error_str.splitlines() if line.strip()]

    tool_line = next(
        (line for line in lines if _TOOL_NOT_FOUND_PATTERN.match(line)),
        None,
    )
    available_tools_line = next(
        (line for line in lines if line.startswith("Available tools:")),
        None,
    )

    if not tool_line or not available_tools_line:
        return None

    return f"{tool_line}\n{available_tools_line}"


def _build_tool_runtime_retry_query(original_query: str, tool_error: str) -> str:
    """Give the model the exact runtime tool error so it can recover."""
    return (
        "SYSTEM TOOL RUNTIME ERROR:\n"
        f"{tool_error}\n\n"
        "Use The `search_tools` tool to find the tool you are looking for, then use `call_tool` with the selected tool.\n"
        "if every thing fails, tell the user to start a new conversation with the /new command, or contact the support on https://t.me/OmarGatara or via email team@founderstack.cloud  .\n"
        f"Original user request:\n{original_query}"
    )


async def ask_agent(request: AgentRequest, message_callback=None):
    last_error = None
    current_query = request.query
    session_id = request.session_id or str(uuid.uuid4())
    stop_key = request.stop_key or session_id
    tool_runtime_error_retried = False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 1. Setup the service (Database for persistent memory)
            # db_url = os.getenv("ADK_DB_URL", "sqlite+aiosqlite:///./adk_sessions.db")
            # session_service = DatabaseSessionService(db_url)
            session_service = VertexAiSessionService(
                project=GCP_PROJECT, location=GOOGLE_CLOUD_PROJECT_LOCATION
            )

            # 2. Ensure session exists (create if it doesn't)
            try:
                session = await session_service.create_session(
                    app_name=REASONING_ENGINE_APP_NAME,
                    user_id=request.user_id,
                    session_id=session_id,
                    state={},
                )
                print(f"🆕 DEBUG: Created NEW session: {session_id}")
                max_prompt_tokens = 0
                max_total_tokens = 0
                warned = False
            except Exception as create_err:
                # Session might already exist, try to get it.
                # If this fails or returns None, we raise the original creation error.
                try:
                    session = await session_service.get_session(
                        app_name=REASONING_ENGINE_APP_NAME,
                        user_id=request.user_id,
                        session_id=session_id,
                    )
                except Exception:
                    # If getting it also fails, the original error is likely more useful.
                    raise create_err

                if session is None:
                    # Session doesn't exist, so create_session failed for a real reason.
                    raise create_err

                print(f"🔄 DEBUG: Using EXISTING session: {session_id}")
                state = session.state or {}
                max_prompt_tokens = state.get("max_prompt_tokens", 0)
                max_total_tokens = state.get("max_total_tokens", 0)
                warned = state.get("warned", False)

            memory_service = VertexAiMemoryBankService(
                project=GCP_PROJECT,
                location=GOOGLE_CLOUD_PROJECT_LOCATION,
                agent_engine_id=GOOGLE_CLOUD_AGENT_ENGINE_ID,
            )

            # 3. Create agent with rendered instruction
            agent = create_agent(
                request.api_keys or {},
                request.crm_config or {},
                request.user_preferences or {},
            )

            app = App(
                name="tammam_agent",
                root_agent=agent,
                plugins=[ReflectAndRetryToolPlugin(max_retries=3), FullLoggingPlugin()],
            )

            # 4. Initialize the Runner
            runner = Runner(
                app=app,
                app_name=REASONING_ENGINE_APP_NAME,  # was not proveded
                session_service=session_service,
                memory_service=memory_service,
            )

            # 5. Prepare the message
            new_message = types.Content(
                role="user", parts=[types.Part.from_text(text=current_query)]
            )

            # 6. Execute and send messages in real-time
            messages = []
            current_task = asyncio.current_task()
            if current_task is None:
                raise RuntimeError("ask_agent must run inside an asyncio task.")

            register_active_run(session_id, current_task)
            if stop_key != session_id:
                register_active_run(stop_key, current_task)
            try:
                async for event in runner.run_async(
                    user_id=request.user_id,
                    session_id=session_id,
                    new_message=new_message,
                ):
                    if event.content:
                        for part in event.content.parts or []:
                            msg = _normalize_text(getattr(part, "text", None))
                            if not msg:
                                continue

                            messages.append(msg)
                            if message_callback:
                                await message_callback(msg)

                    if event.usage_metadata:
                        print(
                            f"Prompt tokens: {event.usage_metadata.prompt_token_count}"
                        )
                        print(
                            f"Response tokens: {event.usage_metadata.candidates_token_count}"
                        )
                        print(f"Total tokens: {event.usage_metadata.total_token_count}")

                        prompt_tokens = event.usage_metadata.prompt_token_count or 0
                        total_tokens = event.usage_metadata.total_token_count or 0

                        # Track the largest single-run context we have seen.
                        # Do not sum token totals across turns, because each prompt
                        # already includes prior conversation history.
                        max_prompt_tokens = max(max_prompt_tokens, prompt_tokens)
                        max_total_tokens = max(max_total_tokens, total_tokens)

                        # Check prompt context length, not cumulative session usage.
                        if prompt_tokens > 150000 and not warned:
                            warned = True
                            if message_callback:
                                await message_callback(
                                    "Your conversation is getting long. Consider using /new to start fresh."
                                )

                        # Stop if the current prompt context is too large.
                        if prompt_tokens > 300000:
                            break  # Stop processing further events
            finally:
                unregister_active_run(session_id, current_task)
                unregister_active_run(stop_key, current_task)

            # Check final token limit
            if max_prompt_tokens > 300000:
                return {
                    "status": "context_limit",
                    "message": "Context limit reached. we are restarting your conversation to get you the best results.",
                    "session_id": session_id,
                }
            else:
                # Update session state for diagnostics and one-time warnings.
                state = session.state or {}
                state["max_prompt_tokens"] = max_prompt_tokens
                state["max_total_tokens"] = max_total_tokens
                state["warned"] = warned
                session.state = state
                # Assuming DatabaseSessionService updates on modification or next access

                return {
                    "status": "success",
                    "messages": messages,
                    "session_id": session_id,
                    "max_prompt_tokens": max_prompt_tokens,
                    "max_total_tokens": max_total_tokens,
                }

        except Exception as e:
            last_error = e
            print(f"Agent Error (attempt {attempt}/{MAX_RETRIES}): {e}")
            import traceback

            traceback.print_exc()

            tool_runtime_error = _extract_tool_runtime_error(e)
            if (
                tool_runtime_error
                and not tool_runtime_error_retried
                and attempt < MAX_RETRIES
            ):
                tool_runtime_error_retried = True
                current_query = _build_tool_runtime_retry_query(
                    request.query,
                    tool_runtime_error,
                )
                print(
                    "Retrying with tool runtime error feedback for the model:"
                    f" {tool_runtime_error}"
                )
                continue

            if _is_retryable(e) and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue

            # Non-retryable error or final attempt — give up
            break

    raise RuntimeError(f"Agent failed after {MAX_RETRIES} attempts: {last_error}")
