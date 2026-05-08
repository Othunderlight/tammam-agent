from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

_root_dir = Path(__file__).parent
BASE_INSTRUCTION = (_root_dir / "prompt.md").read_text()
FOUNDERSTACK_CRM_SKILL_TEMPLATE = (
    _root_dir / "skills" / "founderstack-crm-toolkit" / "SKILL.md"
).read_text()


def _get_crm_replacements(crm_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and format CRM-related placeholders.
    """
    replacements = {}

    # Replace stage_choices - API returns: [{"label": "Lead"}, ...] or ["Lead", "Contact"]
    pipeline_stages = crm_config.get("pipeline_stages", [])
    stages = []
    for s in pipeline_stages:
        if isinstance(s, dict):
            label = s.get("label", "")
            if label:
                stages.append(label)
        elif isinstance(s, str):
            stages.append(s)
    replacements["{{ stage_choices }}"] = (
        ", ".join(stages) if stages else "Lead, Contact, Customer"
    )

    # Replace type_choices - API returns: [{"label": "Prospect"}, ...] or ["Prospect", "Customer"]
    lead_types = crm_config.get("lead_types", [])
    types = []
    for t in lead_types:
        if isinstance(t, dict):
            label = t.get("label", "")
            if label:
                types.append(label)
        elif isinstance(t, str):
            types.append(t)
    replacements["{{ type_choices }}"] = (
        ", ".join(types) if types else "Prospect, Customer"
    )

    # Replace lead_source_choices - API returns: [{"label": "Website"}, ...] or ["Website", "Referral"]
    lead_sources = crm_config.get("lead_sources", [])
    sources = []
    for s in lead_sources:
        if isinstance(s, dict):
            label = s.get("label", "")
            if label:
                sources.append(label)
        elif isinstance(s, str):
            sources.append(s)
    replacements["{{ lead_source_choices }}"] = (
        ", ".join(sources) if sources else "Inbound, Outbound"
    )

    # Replace interaction_type_choices - API returns: ["Call: description", "Email", ...]
    interaction_types = crm_config.get("interaction_types", [])
    type_choices = []
    for t in interaction_types:
        if isinstance(t, str):
            type_choices.append(t)
        elif isinstance(t, dict):
            name = t.get("name", "")
            if name:
                type_choices.append(name)

    if type_choices:
        replacements["{{ interaction_type_choices }}"] = "- " + "\n- ".join(
            type_choices
        )
    else:
        replacements["{{ interaction_type_choices }}"] = (
            "- Ask user to define one and use create_interaction_type."
        )

    return replacements


def _get_identity_replacements(
    user_preferences: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Extract and format user preference-related placeholders.
    """
    preferences = user_preferences or {}
    # Use desired_communication_style as in the teammate's diff
    style = preferences.get("desired_communication_style")
    if not style:
        # Fallback to the old key just in case
        style = preferences.get("user_prefrence", "")

    if isinstance(style, str):
        style = style.strip()
    else:
        style = ""

    if not style:
        style = "No additional communication-style preference was provided. Follow the default style rules above."

    return {"{{desired_communication_style}}": style}


def _get_system_replacements() -> Dict[str, str]:
    """
    Extract and format system-related placeholders.
    """
    return {"{{ today_date }}": date.today().strftime("%Y-%m-%d")}


def render_instruction(
    crm_config: Dict[str, Any], user_preferences: Optional[Dict[str, Any]] = None
) -> str:
    """
    Render the instruction by replacing placeholders with context values.

    Args:
        crm_config: Dict with pipeline_stages, lead_types, lead_sources from CRM API.
        user_preferences: Dict with user-level prompt preferences.

    Returns:
        Instruction string with placeholders replaced
    """
    replacements = {}
    replacements.update(_get_crm_replacements(crm_config))
    replacements.update(_get_identity_replacements(user_preferences))
    replacements.update(_get_system_replacements())

    instruction = BASE_INSTRUCTION
    for placeholder, value in replacements.items():
        instruction = instruction.replace(placeholder, value)

    return instruction


def render_crm_skill_instruction(crm_config: Dict[str, Any]) -> str:
    """Render CRM skill instructions from template placeholders."""
    replacements = _get_crm_replacements(crm_config)
    instruction = FOUNDERSTACK_CRM_SKILL_TEMPLATE
    for placeholder, value in replacements.items():
        instruction = instruction.replace(placeholder, value)
    return instruction
