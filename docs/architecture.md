# AI Service Architecture (FastAPI + Inngest + Django)

This document outlines the interaction between the React Frontend, Django Backend, and the FastAPI AI Service.

## Core Principles
- **Separation of Concerns:** Django handles business logic and persistent state; FastAPI handles AI processing and orchestration.
- **Decoupling:** Django triggers actions via HTTP, remaining agnostic to the underlying AI implementation.
- **Security:** Token-based authentication using shared RSA keys (RS256).

---

## 1. User-Triggered Request (Logic 1)
**Purpose:** Real-time AI features triggered by a user in the UI (e.g., "Summarize this lead").

### Flow:
1. **React:** Sends request to FastAPI with the user's Django JWT.
2. **FastAPI:** Verifies the JWT using the shared Public Key.
3. **Execution:** FastAPI performs AI tasks and updates Django via API using the user's context.

### Technical Spec:
- **Endpoints:** 
  - `POST /ai/process-lead`: General AI processing.
  - `POST /ai/parse-conversation`: Specifically for parsing raw chat logs into CRM activities.
- **Headers:** 
  - `Authorization: Bearer <DJANGO_ACCESS_TOKEN>`
  - `Content-Type: application/json`

---

## 2. Auto-Triggered Request (Logic 2)
**Purpose:** Background AI tasks triggered by database changes (e.g., "Auto-generate reply to new email").

### Flow:
1. **Django Signal:** `post_save` on a model (e.g., `ActivityLog`) sends a POST to FastAPI.
2. **FastAPI Trigger:** Receives the data and initiates background processing via Inngest.
3. **System Auth:** FastAPI generates a "System" JWT (signed with Private Key) to communicate back to Django securely.

### Technical Spec:
- **Trigger URL:** `POST /trigger/activity-log`
- **Payload:** Includes relevant record IDs and content to be processed.

---

## 3. Security Details (RS256)
- **Encryption:** RS256 (RSA Signature).
- **Public Key (`jwt_public_key.pem`):** Used by FastAPI to verify user-sent JWTs.
- **Private Key (`jwt_private_key.pem`):** Used by FastAPI to sign system requests to Django.
- **JWT Claims:** System tokens include `user_id`, `token_type: "access"`, and standard claims for Django compatibility.

---

## 4. Inngest: The Nervous System
All heavy or multi-step AI tasks are offloaded to **Inngest**.
- **Event-Driven:** FastAPI receives a trigger and emits an Inngest event.
- **Resilience:** Inngest handles retries, delays, and state management for complex workflows.
- **Functions:** Located in `inngest_client.py`.
