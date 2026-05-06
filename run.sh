INNGEST_DEV=1 uv run uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080

docker run -p 8288:8288 --add-host=host.docker.internal:host-gateway inngest/inngest   inngest dev -u http://host.docker.internal:8080/api/inngest --no-discovery


# debugging:
# delete webhook
curl -s "https://api.telegram.org/botTOKEN/deleteWebhook"
# set webhook
curl -s -F "url=https://unexpendable-unresponsively-tawana.ngrok-free.dev/webhooks/telegram" "https://api.telegram.org/botTOKEN/setWebhook"

# for telgram webhook:
- uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
- ngrok http --domain=unexpendable-unresponsively-tawana.ngrok-free.dev 8080
- uv run python integrations/telegram/set_webhook.py
export PYTHONPATH=$PYTHONPATH:. && adk run ai/workflows/g_adk/tool_agent

export PYTHONPATH=$PYTHONPATH:. && adk web ai/workflows/g_adk/
