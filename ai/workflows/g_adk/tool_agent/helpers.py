from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

_root_dir = Path(__file__).parent
BASE_INSTRUCTION = (_root_dir / "prompt.md").read_text()


def render_instruction(
    crm_config: Dict[str, Any], user_preferences: Optional[Dict[str, Any]] = None
) -> str:
    """
    Render the instruction by replacing placeholders with CRM config values.

    Args:
        crm_config: Dict with pipeline_stages, lead_types, lead_sources from CRM API.
        user_preferences: Dict with user-level prompt preferences.

    Returns:
        Instruction string with placeholders replaced
    """
    instruction = BASE_INSTRUCTION

    # Replace stage_choices - API returns: [{"label": "Lead"}, ...] or ["Lead", "Contact"]
    pipeline_stages = crm_config.get("pipeline_stages", [])
    if pipeline_stages:
        stages = []
        for s in pipeline_stages:
            if isinstance(s, dict):
                # Expected format: {"label": "Lead"}
                label = s.get("label", "")
                if label:
                    stages.append(label)
            elif isinstance(s, str):
                # Alternative format: just "Lead"
                stages.append(s)
        if stages:
            stage_str = ", ".join(stages)
            instruction = instruction.replace("{{ stage_choices }}", stage_str)
        else:
            instruction = instruction.replace(
                "{{ stage_choices }}", "Lead, Contact, Customer"
            )
    else:
        instruction = instruction.replace(
            "{{ stage_choices }}", "Lead, Contact, Customer"
        )

    # Replace type_choices - API returns: [{"label": "Prospect"}, ...] or ["Prospect", "Customer"]
    lead_types = crm_config.get("lead_types", [])
    if lead_types:
        types = []
        for t in lead_types:
            if isinstance(t, dict):
                # Expected format: {"label": "Prospect"}
                label = t.get("label", "")
                if label:
                    types.append(label)
            elif isinstance(t, str):
                # Alternative format: just "Prospect"
                types.append(t)
        if types:
            type_str = ", ".join(types)
            instruction = instruction.replace("{{ type_choices }}", type_str)
        else:
            instruction = instruction.replace(
                "{{ type_choices }}", "Prospect, Customer"
            )
    else:
        instruction = instruction.replace("{{ type_choices }}", "Prospect, Customer")

    # Replace lead_source_choices - API returns: [{"label": "Website"}, ...] or ["Website", "Referral"]
    lead_sources = crm_config.get("lead_sources", [])
    if lead_sources:
        sources = []
        for s in lead_sources:
            if isinstance(s, dict):
                label = s.get("label", "")
                if label:
                    sources.append(label)
            elif isinstance(s, str):
                sources.append(s)
        if sources:
            source_str = ", ".join(sources)
            instruction = instruction.replace("{{ lead_source_choices }}", source_str)
        else:
            instruction = instruction.replace(
                "{{ lead_source_choices }}", "Inbound, Outbound"
            )
    else:
        instruction = instruction.replace(
            "{{ lead_source_choices }}", "Inbound, Outbound"
        )

    # Replace interaction_type_choices - API returns: ["Call: description", "Email", ...]
    interaction_types = crm_config.get("interaction_types", [])
    if interaction_types:
        type_choices = []
        for t in interaction_types:
            if isinstance(t, str):
                type_choices.append(t)
            elif isinstance(t, dict):
                name = t.get("name", "")
                if name:
                    type_choices.append(name)
        if type_choices:
            types_str = "\n      -- " + "\n      -- ".join(type_choices)
            instruction = instruction.replace(
                "{{ interaction_type_choices }}", types_str
            )
        else:
            instruction = instruction.replace(
                "{{ interaction_type_choices }}",
                "Please ask the user what to add as an interaction type because there is none configured, use the create_interaction_type tool when the user wants to add one.",
            )
    else:
        instruction = instruction.replace(
            "{{ interaction_type_choices }}",
            "Please ask the user what to add as an interaction type because there is none configured, use the create_interaction_type tool when the user wants to add one.",
        )

    preferences = user_preferences or {}

    desired_communication_style = preferences.get("desired_communication_style")
    if isinstance(desired_communication_style, str):
        desired_communication_style = desired_communication_style.strip()
    else:
        desired_communication_style = ""

    if desired_communication_style:
        instruction = instruction.replace(
            "{{desired_communication_style}}", desired_communication_style
        )
    else:
        instruction = instruction.replace(
            "{{desired_communication_style}}",
            "No additional communication-style preference was provided. Follow the default style rules above.",
        )

    today_date = date.today().strftime("%Y-%m-%d")
    instruction = instruction.replace("{{ today_date }}", today_date)

    return instruction
