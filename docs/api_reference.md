# API Reference & Tool Integration

This document details how the AI service interacts with the Django backend and how tools are configured.

---

## 1. User Preferences API
Manage individual user settings and preferences dynamically to customize AI behavior.

### Endpoints (Django)
- `GET /api/user-preferences/my-preferences/`: Fetch all settings for the current user.
- `POST /api/user-preferences/my-preferences/`: Update or bulk-create preferences.

### AI Integration (`ai/tools/usr/prefrence.py`)
The AI service fetches these preferences to customize the system prompt or agent behavior (e.g., tone of voice, theme, notification settings).

---

## 2. CRM Configuration
To ensure the AI understands the specific CRM setup, it fetches organization-wide config.

### Fetcher (`ai/tools/crm_config.py`)
Retrieves:
- **Pipeline Stages**: The labels for the sales funnel.
- **Lead Types & Sources**: Valid categories for leads.
- **Interaction Types**: Valid types of activities (e.g., "Email", "Meeting").

---

## 3. Internal AI Endpoints

### Conversation Parsing
`POST /ai/parse-conversation`
- **Payload**: `person_id`, `conversation_text`, `person_name`.
- **Behavior**: Queues an Inngest job to parse text into structured activities.

### Activity Triggers
`POST /trigger/activity-log`
- **Payload**: Activity data from Django.
- **Behavior**: Triggers the AI recommendation engine to suggest the next step for that lead.

### Email Service
`POST /trigger/send-email`
- **Payload**: `to`, `subject`, `body`.
- **Behavior**: Offloads email sending to a background queue.

---

## 4. Integration Webhooks

### Telegram
- `POST /webhooks/telegram`: Primary receiver for Telegram Bot updates.
- `GET /webhooks/telegram/health`: Checks webhook status and configuration.

### WhatsApp
- Routes are registered dynamically via `integrations/whatsapp/client.py`.
