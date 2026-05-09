import os
from typing import Any, Dict, List, Optional

from ai.runs.stop_registry import is_stop_requested
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
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

model = Gemini(model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))


def create_composio_agent(composio_api_key) -> Agent:

    composio_mcp_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://connect.composio.dev/mcp",
            headers={
                "x-consumer-api-key": composio_api_key,
                "Content-Type": "application/json",
            },
        ),
    )

    # composio_skill = load_skill_from_dir(_root_dir / "skills" / "composio")
    # composio_skill_toolset = SkillToolset(
    #     skills=[composio_skill],
    #     additional_tools=[composio_mcp_toolset],
    # )

    return Agent(
        name="composio_agent",
        model=model,
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL,
            )
        ),
        description="The Composio agent",
        # include_contents="none", now the agent can remeber throght the session
        # instruction="you are helpful assitant that reply only in 3 words max",
        instruction="you have composio skill and tools, whihc can make you over than +1000 apps, use them to help the user out, make sure the tool is connected and authorized before you use it, if not give the user the link to connect it",
        tools=[composio_mcp_toolset],
    )


# Default agent (without user-specific config)
composio_agent = create_composio_agent("none")
