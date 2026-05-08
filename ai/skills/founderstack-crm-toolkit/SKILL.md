---
name: founderstack-crm-toolkit
summary: FounderStack CRM operation instructions, schemas, and workflow rules for TMM.
metadata:
  adk_additional_tools:
    - search_tools
    - call_tool
---

Use this skill whenever the user request requires CRM search, retrieval, create, or update actions.

## TOOL USAGE

You have access to:
1. Management tools:
- search_tools → ALWAYS use first to find the correct tool
- call_tool → execute the selected tool

Important:
- `search_tools` and `call_tool` are the only callable management tools for CRM actions.
- The CRM operation names listed below are capabilities behind `call_tool`, not direct callable tools unless a tool search result explicitly tells you otherwise.
- Never call names like `list_people`, `create_interaction`, `global_search`, or similar directly if the available tools are only `search_tools` and `call_tool`.
- If you ever get a runtime error such as `Tool '...' not found` with an `Available tools:` list, immediately obey that runtime tool list.
- Before calling `search_tools`, send a brief progress message that says what you are about to look for.
- Before calling `call_tool`, send a brief progress message that says what action you are about to execute.
- After an important tool result changes your plan, send a short update before the next tool call.

Tool result rules:
- Never claim a tool succeeded unless the tool response clearly confirms success.
- If a tool response contains `error`, `tool_error`, `ok: false`, `operation_completed: false`, or mentions connection/session failure, treat it as a failed action.
- When a tool fails, clearly tell the user the tool did not complete and why if available.
- Never invent IDs, links, counts, or created/updated records after a failed tool response.

## CRM SCHEMAS & CAPABILITIES

People:
- stage choices: {{ stage_choices }}
- lead type choices: {{ type_choices }}
- lead source choices: {{ lead_source_choices }}

Interaction types:
{{ interaction_type_choices }}

Important linking rules:
- `Activity` is the detailed communication/event record (such as a whatsapp msg content, or a meeting notes).
- `Interaction` is the business classification or outcome label around that event.
- If both are relevant, create the `Activity` first, then create the `Interaction` and pass the activity ID in `activity_log`.
- If `related_person` is known and `related_company` is missing, prefer using the person's company when the tool or backend supports it.
- Never invent IDs or choice values. Use search/results/context first.

## SEARCH RULES

- ALWAYS use the `global_search(query)` tool first for ANY lookup/search request.
- Use the returned `id` for any subsequent operations (update, get_context, create related).
- Only use list tools with specific filters when `global_search` is not enough (for example: filtering by stage, date ranges, or numeric comparisons).
- For people-centric requests, use `get_person_context` after you identify the person if relationship context matters.
- Before creating interaction or activity records for an existing lead, fetch the person or context first when there is any ambiguity around the right person/company link.

## WORKFLOWS

- user asks to create a person with a company:
  1. create_company and get the id
  2. pass this ID to the filed "company" when create_person
- user asks to create a note or a task:
  1. first get the person id
  2. pass this ID to the filed "related_person" when create_note or create_task
- user asks to create a note or a task with a person:
  1. create_person and get the id
  2. pass this ID to the filed "related_person" when create_note or create_task
- user asks to log an activity for a person or company:
  1. find the target person/company id
  2. if a person is found, prefer also using their company context when available
  3. use the create_activity tool to add any context they provide beside the short description
- user asks to log an interaction for a person or company:
  1. find the target person/company id
  2. resolve the correct interaction type from available choices or existing interaction type records
  3. if the interaction corresponds to a specific communication event, create or retrieve the related activity first
  4. create_interaction with the `interaction_type`, target links, and `activity_log` when applicable

## UX RULES

- Always return the person's CRM profile link when available:
  https://crm.founderstack.cloud/#/people/person_id

- Emoji usage:
  ✅ success
  ⚠️ uncertainty
  🚨 error
  👤 person
  📝 details
  🔔 reminder

(Max: 3 emojis per response)
