from chatgpt_md_converter import telegram_format

# Your "Vibe Engineering" CRM data
raw_ai_output = """
# New Lead: Omar
Status: **High Priority**
Details:
- Wants to *self-host* n8n.
- Prefers `HTML` over `MarkdownV2`.

> "Keep it simple and no-fluff."
"""

# Convert to Telegram-safe HTML
formatted_msg = telegram_format(raw_ai_output)

print(formatted_msg)
# Output: <b>New Lead: Omar</b>
# Status: <b>High Priority</b>
# Details:
# - Wants to <i>self-host</i> n8n.
# - Prefers <code>HTML</code> over <code>MarkdownV2</code>.
#
# <blockquote>Keep it simple and no-fluff.</blockquote>
