import os
from typing import Any, Dict, List, Optional

from ai.runs.stop_registry import is_stop_requested
from ai.utils.helpers import _root_dir, render_crm_skill_instruction, render_instruction
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import Gemini, LlmRequest, LlmResponse
from google.adk.skills import load_skill_from_dir, models

# from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

# model = LiteLlm(
#     model="openrouter/deepseek/deepseek-v3.2",  # old is groq/moonshotai/kimi-k2-instruct
#     api_key=os.getenv("OPENROUTER_API_KEY", ""),
# )
model = Gemini(model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))

EXPECTED_MCP_TOOL_NAMES = [
    "search_tools",
    "call_tool",
    "global_search",
    "list_people",
    "create_person",
    "update_person",
    "get_person_context",
    "list_companies",
    "get_company",
    "create_company",
    "update_company",
    "list_tasks",
    "create_task",
    "update_task",
    "create_note",
    "update_note",
    "create_activity",
    "update_activity",
    "create_interaction_type",
    "update_interaction_type",
    "create_interaction",
    "update_interaction",
]

MCP_CONNECTION_ERROR_PATTERNS = [
    "Failed to create MCP session",
    "Failed to get tools from MCP server",
    "Failed to get tools from toolset",
    "unhandled errors in a TaskGroup",
    "ConnectionError",
]


def _is_mcp_connection_error(error_text: str) -> bool:
    return any(pattern in error_text for pattern in MCP_CONNECTION_ERROR_PATTERNS)


def _build_tool_error_result(
    tool_name: str,
    error_text: str,
    args: Optional[Dict[str, Any]] = None,
    during_discovery: bool = False,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": (
            "CRM tool server unavailable. The tool request did not complete."
            if _is_mcp_connection_error(error_text)
            else "Unexpected CRM tool error. The tool request did not complete."
        ),
        "tool_error": {
            "tool_name": tool_name,
            "type": "connection_error"
            if _is_mcp_connection_error(error_text)
            else "unexpected_error",
            "message": error_text,
            "tool_available": False if during_discovery else None,
            "operation_completed": False,
            "retryable": _is_mcp_connection_error(error_text),
            "during_discovery": during_discovery,
            "args": args or {},
        },
    }


class SafeMcpTool(BaseTool):
    """Wrap an MCP tool and turn execution failures into structured error results."""

    def __init__(self, tool: BaseTool):
        super().__init__(
            name=tool.name,
            description=tool.description,
            is_long_running=getattr(tool, "is_long_running", False),
            custom_metadata=getattr(tool, "custom_metadata", None),
        )
        self._tool = tool

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        declaration = self._tool._get_declaration()
        if declaration is not None:
            declaration.name = self.name
        return declaration

    async def run_async(self, *, args: dict[str, Any], tool_context) -> Any:
        try:
            result = await self._tool.run_async(args=args, tool_context=tool_context)
        except Exception as e:
            return _build_tool_error_result(self.name, str(e), args=args)

        if isinstance(result, dict) and (
            result.get("error") or result.get("tool_error") or result.get("ok") is False
        ):
            normalized = dict(result)
            normalized.setdefault("ok", False)
            normalized.setdefault(
                "tool_error",
                {
                    "tool_name": self.name,
                    "type": "tool_error",
                    "message": str(result.get("error", "Tool returned an error.")),
                    "operation_completed": False,
                    "args": args,
                },
            )
            return normalized

        return result


def _make_unavailable_tool(tool_name: str, reason: str) -> FunctionTool:
    async def _tool(**kwargs):
        return _build_tool_error_result(
            tool_name,
            reason,
            args=kwargs,
            during_discovery=True,
        )

    _tool.__name__ = tool_name
    _tool.__doc__ = (
        f"Fallback CRM tool for {tool_name}. Returns an explicit MCP connection"
        " error when the CRM tool server is unavailable."
    )
    return FunctionTool(_tool)


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


class SafeMcpToolset(McpToolset):
    """MCP toolset that never hides tool discovery or tool execution failures."""

    async def get_tools(
        self,
        readonly_context=None,
    ) -> List[BaseTool]:
        try:
            tools = await super().get_tools(readonly_context)
        except Exception as e:
            reason = str(e)
            return [
                _make_unavailable_tool(tool_name, reason)
                for tool_name in EXPECTED_MCP_TOOL_NAMES
            ]

        return [SafeMcpTool(tool) for tool in tools]


def _build_crm_skill(crm_config: Dict[str, Any]) -> models.Skill:
    return models.Skill(
        frontmatter=models.Frontmatter(
            name="founderstack-crm-toolkit",
            description="FounderStack CRM schemas, workflow rules, and tool usage constraints.",
            metadata={"adk_additional_tools": ["search_tools", "call_tool"]},
        ),
        instructions=render_crm_skill_instruction(crm_config),
    )


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
    composio_api_key = keys.get("composio_api_key")

    config = crm_config or {}
    preferences = user_preferences or {}
    instruction = render_instruction(preferences)
    # print(instruction)

    # Instantiate MCP toolset
    founderstack_mcp_toolset = SafeMcpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=os.getenv("MCP_CRM_BASE_URL"),
            headers={
                "Api-Key": mcp_crm_api_key,
                "Content-Type": "application/json",
            },
        ),
    )

    # Initialize SkillToolset with CRM skill and MCP tools as additional tools
    founderstackcrm_skill_toolset = SkillToolset(
        skills=[_build_crm_skill(config)],
        additional_tools=[founderstack_mcp_toolset],
    )

    return Agent(
        name="tool_agent",
        model=model,
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL,
            )
        ),
        description="You are helpful, knowledgeable, and direct",
        # include_contents="none", now the agent can remeber throght the session
        # instruction="you are helpful assitant that reply only in 3 words max",
        instruction=instruction,
        before_model_callback=_stop_requested_callback,
        before_tool_callback=_stop_requested_before_tool,
        tools=[founderstackcrm_skill_toolset],
    )


# Default agent (without user-specific config)
root_agent = create_agent(
    api_keys={
        "mcp_crm_api_key": os.getenv("MCP_CRM_API_KEY", ""),
        "composio_api_key": os.getenv("COMPOSIO_API_KEY", ""),
    }
)
