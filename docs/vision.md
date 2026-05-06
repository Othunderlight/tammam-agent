# FounderStack: Technical Vision & Execution

This document defines the "AI Decision Engine" strategy for FounderStack, bridging the product goals with our architectural implementation.

---

## 1. The "AI Brain" Architecture
Our tech stack follows a biological metaphor for AI orchestration:
- **Memory (Django):** The source of truth. Stores raw conversations, people, deals, and history.
- **Intelligence (FastAPI + LLMs):** The cognitive layer. Extracts intent, summarizes context, and generates suggestions.
- **Nerves (Inngest):** The autonomous layer. Triggers background workflows (reminders, status changes, parsing) without user lag.

---

## 2. Key AI Capabilities

### A. Conversation Extraction
*Goal: Convert raw noise into CRM signal.*
- **Logic:** Take raw text from a paste or integration -> Use LLM to identify Summary, Intent, and Next Steps.
- **Action:** Automatically create `Activities` and `Tasks` in Django.

### B. Context-Aware Recommendations
*Goal: Answer "What do I do next?"*
- **Logic:** When an activity is logged, the AI reviews the last 5 interactions and organization knowledge base.
- **Action:** Generates a `recommended_action` field on the Person record.

### C. Unified Communications Integration
*Goal: Meet founders where they work.*
- **Logic:** Bridging Telegram and WhatsApp into the AI workflow.
- **Action:** Users can talk to the "Agent" via messaging apps to update the CRM or get insights.

---

## 3. Development Roadmap

### Phase 1: Context & Extraction (Current)
- Implementation of the `parse_conversation` workflow.
- Structured LLM output handling in `services/llm.py`.
- Security bridge between FastAPI and Django.

### Phase 2: Autonomous Workflows (In Dev)
- **Stalled Conversation Detection:** Inngest triggers if a lead is ignored for >3 days.
- **Status Automation:** Moving a lead to "Interested" automatically schedules a follow-up.
- **Manager/Sub-Agent Architecture:** Moving from a single agent to specialized agents for different tasks.

### Phase 3: The Decision Dashboard
- Priority scoring based on AI sentiment analysis.
- Daily "Nudge" generation: "You haven't replied to X in 2 days."

---

## 4. Operational Guardrails
- **Human-in-the-Loop:** The AI suggests; it does not unilaterally change status or send messages without user confirmation (or a task being marked done).
- **Context Lock:** Every AI call must be grounded in real CRM data to prevent hallucinations.
