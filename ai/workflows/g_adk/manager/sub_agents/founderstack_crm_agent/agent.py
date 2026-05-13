import os
from typing import Any, Dict

from ai.utils.adk_safe import SafeMcpToolset
from ai.utils.helpers import render_crm_skill_instruction
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.skills import models
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

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


# def _build_crm_skill(crm_config: Dict[str, Any]) -> models.Skill:
#     return models.Skill(
#         frontmatter=models.Frontmatter(
#             name="founderstack-crm-toolkit",
#             description="FounderStack CRM schemas, workflow rules, and tool usage constraints.",
#             metadata={"adk_additional_tools": ["search_tools", "call_tool"]},
#         ),
#         instructions=render_crm_skill_instruction(crm_config),
#     )


def create_founderstack_crm_agent(
    mcp_crm_api_key, crm_config: Dict[str, Any] = None
) -> Agent:

    config = crm_config or {}
    instructions = render_crm_skill_instruction(config)
    # Append the specialized tool-user instruction
    instructions += (
        "\n\nYou are a specialized tool-user. Your ONLY source of truth is the output of your tools. "
        "If your tools fail, return an error message to the manager agent. "
        "DO NOT generate data from your own memory."
    )

    # Instantiate MCP toolset
    founderstack_mcp_toolset = SafeMcpToolset(
        expected_tool_names=EXPECTED_MCP_TOOL_NAMES,
        connection_params=StreamableHTTPConnectionParams(
            url=str(os.getenv("MCP_CRM_BASE_URL")),
            headers={
                "Api-Key": str(mcp_crm_api_key),
                "Content-Type": "application/json",
            },
        ),
    )

    # Initialize SkillToolset with CRM skill and MCP tools as additional tools

    return Agent(
        name="founderstack_crm",
        model=model,
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL,
            )
        ),
        description="An Agent that can manage founderstack crm",
        # include_contents="none", now the agent can remeber throght the session
        # instruction="you are helpful assitant that reply only in 3 words max",
        instruction=instructions,
        tools=[founderstack_mcp_toolset],
    )


# Default agent (without user-specific config)
founderstack_crm_agent = create_founderstack_crm_agent("none")
