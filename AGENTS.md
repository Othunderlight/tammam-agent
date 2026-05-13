# AGENTS.md - Developer Guide for FounderStack AI Service

## Project Overview

FastAPI-based AI orchestration service for FounderStack CRM. Provides AI-powered features like conversation parsing, activity recommendations, and task automation. Uses Inngest for background job processing.

## Project Structure

```
fastai/
├── main.py              # FastAPI entry point + endpoints
├── auth.py             # JWT authentication utilities
├── inngest_client.py    # Inngest workflow functions
├── ai/                 # AI orchestration layer
│   ├── workflows/      # End-to-end AI workflows
│   ├── tools/          # Reusable tool implementations (CRM, email, calendar)
│   ├── runs/           # Agent execution logic
│   └── utils/          # Utility functions
├── integrations/       # Messaging platform integrations (Telegram, WhatsApp, Slack)
├── services/           # Legacy services (being migrated)
└── .env                # Environment variables
```

## Commands

### Running the Server

```bash
# Start FastAPI server with uvicorn
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080

# For Inngest background jobs (run in separate terminal)
docker run -p 8288:8288 inngest/inngest inngest dev -u http://localhost:8080/api/inngest --no-discovery

# Telegram webhook testing (requires ngrok)
ngrok http 8080
uv run python integrations/telegram/set_webhook.py
```

### Running Tests

This project uses pytest-style test files that run as standalone scripts:

```bash
# Run a specific test file
uv run python test_agent.py
uv run python test_tool_output.py
uv run python test_with_user.py

# Run ADK agent locally
export PYTHONPATH=$PYTHONPATH:. && adk run ai/workflows/g_adk/tool_agent

# Run ADK web interface
export PYTHONPATH=$PYTHONPATH:. && adk web ai/workflows/g_adk/
```

### Linting/Type Checking

No formal linting configured. Run with type checks:

```bash
# Install dependencies
pip install -r reqs.txt

# For manual type checking (if mypy installed)
uv run mypy .
```

### Code Formatting

No auto-formatter configured. Manually format code to match existing style:

- 4 spaces for indentation
- Maximum line length ~120 characters
- One blank line between top-level definitions

## Code Style Guidelines

### Imports

- Standard library imports first, then third-party, then local
- Use absolute imports (e.g., `from ai.tools.crm_depricated import create_person`)
- Group by: stdlib → external → local
- Sort alphabetically within groups

```python
# Correct
import os
import time
from pathlib import Path

import httpx
import inngest
from fastapi import FastAPI

from ai.tools.crm_depricated import create_person
from auth import generate_system_token
```

### Type Hints

- Use type hints for all function parameters and return values
- Use `Optional[X]` instead of `X | None` for compatibility
- Use built-in collection types: `list`, `dict`, `set`

```python
# Correct
def list_people(apikey: str, **filters) -> dict:
    ...

def get_person(apikey: str, person_id: str) -> dict:
    ...

# Async functions
async def handle_activity_log(ctx: inngest.Context) -> dict:
    ...
```

### Naming Conventions

- **Functions/variables**: `snake_case` (e.g., `list_people`, `get_person_context`)
- **Classes**: `PascalCase` (e.g., `BaseIntegration`, `ApiKeyContext`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `BASE_URL`, `DJANGO_API_URL`)
- **Private members**: `_leading_underscore` (e.g., `_api_key_var`)

### Pydantic Models

Use Pydantic `BaseModel` for request/response validation:

```python
from pydantic import BaseModel
from typing import Optional

class ParseConversationRequest(BaseModel):
    person_id: str
    conversation_text: str
    person_name: Optional[str] = "Contact"
    channel_hint: Optional[str] = None
```

### Error Handling

- Use `response.raise_for_status()` for HTTP errors
- Wrap async operations in try/except for Inngest functions
- Use Inngest's logger: `ctx.logger.info()`, `ctx.logger.error()`

```python
async with httpx.AsyncClient() as client:
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        ctx.logger.error(f"Operation failed: {e}")
        return {"status": "error", "detail": str(e)}
```

### Async/Await

- Use `async def` for FastAPI endpoints and Inngest functions
- Use `await` for all async operations
- Use `with httpx.Client()` for sync, `async with httpx.AsyncClient()` for async

```python
# Synchronous (preferred for simple API calls)
with httpx.Client() as client:
    response = client.get(url, headers=headers)

# Asynchronous (for FastAPI endpoints and Inngest)
async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers)
```

### Documentation

Use Google-style docstrings:

```python
def create_person(
    apikey: str,
    name: str,
    email: str = None,
    ...
) -> dict:
    """
    Create a new person.

    Args:
        apikey: API key for authentication.
        name: The full name of the person (required).
        email: Professional or personal email address.
        ...

    Returns:
        JSON response with created person.
    """
```

### Context Managers

Use context managers for resource cleanup:

```python
# Synchronous
with httpx.Client() as client:
    response = client.get(url)

# Asynchronous  
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# Custom context managers
class ApiKeyContext:
    def __init__(self, key: str):
        self.key = key

    async def __aenter__(self):
        set_api_key(self.key)
        return self

    async def __aexit__(self, *args):
        clear_api_key()
```

## Environment Variables

Required variables in `.env`:

- `DJANGO_API_URL` - Django API URL (default: `http://localhost:8000/api`)
- `ALLOWED_ORIGINS` - CORS allowed origins (comma-separated)
- `JWT_PRIVATE_KEY_PATH` - Path to RSA private key
- `JWT_PUBLIC_KEY_PATH` - Path to RSA public key
- LLM provider API keys (Gemini, OpenAI, etc.)

## Key Patterns

### API Client Functions

```python
def list_people(apikey: str, **filters) -> dict:
    """List/search people with optional filters."""
    headers = {"Authorization": f"Api-Key {apikey}"}
    
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/people/", headers=headers, params=filters)
        response.raise_for_status()
        return response.json()
```

### Inngest Functions

```python
@inngest_client.create_function(
    fn_id="my_function",
    trigger=inngest.TriggerEvent(event="my/event"),
)
async def my_handler(ctx: inngest.Context) -> dict:
    """Handle the triggered event."""
    event_data = ctx.event.data
    ctx.logger.info(f"Processing: {event_data}")
    
    # ... processing logic ...
    
    return {"status": "success", "data": ...}
```

### FastAPI Endpoints

```python
@app.post("/ai/endpoint")
async def my_endpoint(
    request: MyRequestModel,
    user_data: dict = Depends(verify_token)
):
    """Endpoint description."""
    await inngest_client.send(inngest.Event(name="event", data={...}))
    return {"status": "processing"}
```
