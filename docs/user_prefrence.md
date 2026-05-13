# User Preferences API

Manage individual user settings and preferences dynamically.

## Authentication

All endpoints require an API key passed via the `Authorization` header:

```bash
Authorization: Api-Key <your-api-key>
```

## Endpoints

All endpoints are prefixed with `/api/user-preferences/`

### Get My Preferences

```
GET /api/user-preferences/my-preferences/
```

Returns the current user's settings and all preferences.

**Example Response:**
```json
{
  "preferences": [
    {"id": 1, "name": "theme", "value": "dark"},
    {"id": 2, "name": "notifications", "value": "true"}
  ]
}
```

### Update My Preferences

```
POST /api/user-preferences/my-preferences/
PATCH /api/user-preferences/my-preferences/
```

Updates or creates preferences for the current user. Supports single preference or a list.

**Body (Single):**

| Field | Description |
|-------|-------------|
| name | Preference name |
| value | Preference value |
| append | (Optional) Boolean. If true, appends value to existing preference instead of replacing. |

**Body (Bulk):**

| Field | Description |
|-------|-------------|
| preferences | Array of {name, value} objects |
| append | (Optional) Boolean. If true, appends values to existing preferences instead of replacing. |

**Example (Bulk with Append):**
```bash
curl -X POST \
  -H "Authorization: Api-Key YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"append": true, "preferences": [{"name": "tags", "value": ",new-tag"}]}' \
  http://localhost:8000/api/user-preferences/my-preferences/
```

### Implementation Details

The endpoint is dynamic. When `append` is false or omitted, it uses `update_or_create` to replace existing values. When `append` is true, it uses `get_or_create` and appends the new string to the existing value.
