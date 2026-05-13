import os
from typing import Any, Dict, List, Optional

from ai.runs.stop_registry import is_stop_requested
from ai.tools.tool_wrapper import manage_user_profile
from ai.utils.helpers import _root_dir, render_crm_skill_instruction, render_instruction
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import Gemini, LlmRequest, LlmResponse
from google.adk.skills import load_skill_from_dir, models
from google.adk.tools.agent_tool import AgentTool

# from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

from .sub_agents.composio_agent.agent import create_composio_agent
from .sub_agents.founderstack_crm_agent.agent import create_founderstack_crm_agent
from .sub_agents.soical_scrabing_agent.agent import create_social_scrape_agent

# model = LiteLlm(
#     model="openrouter/deepseek/deepseek-v3.2",  # old is groq/moonshotai/kimi-k2-instruct
#     api_key=os.getenv("OPENROUTER_API_KEY", ""),
# )
model = Gemini(model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))


def _build_stopped_response() -> LlmResponse:
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Execution stopped by user.")],
        ),
        interrupted=True,
        turnComplete=True,
    )


def _stop_requested_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    del llm_request

    if not is_stop_requested(callback_context.session.id):
        return None

    callback_context._invocation_context.end_invocation = True
    return _build_stopped_response()


async def _stop_requested_before_tool(tool, args, tool_context) -> Optional[dict]:
    del tool, args

    if not is_stop_requested(tool_context._invocation_context.session.id):
        return None

    tool_context._invocation_context.end_invocation = True
    return {"ok": False, "stopped": True, "message": "Execution stopped by user."}


async def auto_save_session_to_memory_callback(callback_context):
    await callback_context.add_session_to_memory()


def create_agent(
    api_keys: Dict[str, str] = None,
    crm_config: Dict[str, Any] = None,
    user_preferences: Dict[str, Any] = None,
) -> Agent:
    """
    Create an agent with the given CRM config.

    Args:
        api_keys: Dict with integration API keys.
        crm_config: Dict with CRM-specific prompt context.
        user_preferences: Dict with user-specific prompt preferences.

    Returns:
        Configured Agent instance
    """
    keys = api_keys or {}
    mcp_crm_api_key = keys.get("mcp_crm_api_key")
    composio_api_key: str | None = keys.get("composio_api_key")
    social_scrape_api_key: str | None = keys.get("social_scrape_api_key")

    config = crm_config or {}
    preferences = user_preferences or {}
    instruction = render_instruction(preferences)
    # print(instruction)

    return Agent(
        name="tammam_agent",
        model=model,
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL,
            )
        ),
        description="The Managar Agent",
        # include_contents="none", now the agent can remeber throght the session
        # instruction="you are helpful assitant that reply only in 3 words max",
        instruction=instruction,
        before_model_callback=_stop_requested_callback,
        before_tool_callback=_stop_requested_before_tool,
        after_agent_callback=auto_save_session_to_memory_callback,
        tools=[
            PreloadMemoryTool(),
            AgentTool(create_composio_agent(composio_api_key)),
            AgentTool(create_founderstack_crm_agent(mcp_crm_api_key, config)),
            AgentTool(create_social_scrape_agent(social_scrape_api_key)),
            # manage_user_profile,
        ],
    )


# Default agent (without user-specific config)
root_agent = create_agent(
    api_keys={
        "mcp_crm_api_key": os.getenv("MCP_CRM_API_KEY", ""),
        "composio_api_key": os.getenv("COMPOSIO_API_KEY", ""),
        "social_scrape_api_key": "none",
    }
)
