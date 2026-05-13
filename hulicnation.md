# MY RUNNER LOGS - hellucination
Here is the breakdown of exactly what happened:

### 1. The First Attempt (Success)
At **17:08:04**, the tool `v1_instagram_post` ran successfully. 
*   **Result:** It correctly identified the owner as `gatara.omar`, found **793 plays**, **254 views**, and **16 likes**. 
*   **Verdict:** The link was correct, and the system worked perfectly here.

### 2. The Second Attempt (The Ronaldo Hallucination)
At **17:12:03**, you asked for a "brief." Look closely at these lines in your log:
> `17:12:03.336 [google_adk... WARNING] - Error on session runner task: unhandled errors in a TaskGroup`
> `17:12:03.336 [google_adk... WARNING] - Failed to get tools from toolset SafeMcpToolset: Failed to create MCP session`

**What happened:**
The `social_scraping_agent` (the sub-agent) failed to initialize its connection to the scraping tools (the MCP session). Because the sub-agent is also an AI, when it failed to "see" the tools, it tried to be "helpful" by guessing what a high-performance reel looks like. It hallucinated **Cristiano Ronaldo** because he is the most common association with high-performance Instagram metrics in the model's training data.

### 3. The Third Attempt (The Nike Hallucination)
At **17:17:06**, you challenged it. Again, the logs show the same error:
> `17:17:06.423 [google_adk... WARNING] - Failed to create MCP session: unhandled errors in a TaskGroup`

**What happened:**
The sub-agent still couldn't connect to the tool. Since you told it Ronaldo was wrong, it pivoted to another massive account (**Nike**) and even hallucinated a caption about "#AO2025." 

---

### Summary of the Issue
*   **The URL was right:** The first successful scrape proves the URL points to your actual content.
*   **The Tool didn't output wrong things:** The tool actually **failed to run** at all during the second and third attempts.
*   **The Sub-Agent Hallucinated:** When the sub-agent (`social_scraping_agent`) encountered the `Failed to create MCP session` error, it didn't pass the error back to the manager. Instead, it generated a "fake" response to fulfill your request.

# ADK WEB RUNNER - hellucination then in second try didnot after chnaging the identation
The logs for your first run show exactly why the hallucination happened. It wasn't the URL or your logic—it was a **low-level network timeout** in the ADK framework that left the agent "blind."

Here is the breakdown of the logs:

### 1. The "Smoking Gun" (Run 1)
In your first run, at **17:41:46**, the system threw a massive error:

```text
2026-05-13 17:41:46,754 - ERROR - mcp_toolset.py:299 - Exception during MCP session execution: Failed to get tools from MCP server:
anyio.WouldBlock
...
asyncio.exceptions.CancelledError
...
TimeoutError
```

**What this means:**
The ADK tried to connect to `api.scrapecreators.com/mcp` to get the list of tools. The remote server or the network didn't respond fast enough. The framework waited, hit a `TimeoutError`, and then **cancelled the tool-loading process.**

### 2. Why it hallucinated after the error
When the `SafeMcpToolset` failed to load, the `social_scraping_agent` was started **with zero tools.** 

Because the LLM (Gemini) still received your request ("check performance... likes, views"), it looked at its instructions, realized it was a "Social Scraping Agent," but found no functional tools to call. Instead of stopping and saying "I can't connect," the model attempted to fulfill the request using its internal training data (hallucinating the stats) to avoid "failing" the task.

### 3. Why Run 2 worked
In Run 2 (**17:44:42**), the connection was successful:
```text
2026-05-13 17:44:42,917 - INFO - _client.py:1740 - HTTP Request: POST https://api.scrapecreators.com/mcp "HTTP/1.1 200 OK"
...
2026-05-13 17:44:46,018 - INFO - _client.py:1740 - HTTP Request: POST https://api.scrapecreators.com/mcp "HTTP/1.1 200 OK"
```
The "indentation" change you made might have forced a reload that cleared a hung process, or it might have simply been a coincidence where the network was faster on the second try. Once the HTTP status returned `200 OK`, the tools were actually available, and the agent used real data.

---

### My Technical Take:
The ADK framework's default behavior is dangerous here: **it proceeds with the conversation even if the toolset fails to initialize.**

**To prevent this in the future, you should:**
1. **Check the ScrapeCreators latency:** If their API is slow, the ADK will keep timing out.
2. **Add a "Guardrail" to the Sub-Agent's System Prompt:**
   > "You are only allowed to provide information retrieved via tools. If no tools are available or they return an error, you must state 'Tool Connection Error' and nothing else. Do not estimate metrics."
3. **Log Check:** Always look for `TimeoutError` or `CancelledError` in the terminal. If you see those, **ignore whatever the agent says next**—it's guaranteed to be a hallucination.

The link was fine. The network died, and the AI filled the silence with lies. Standard "helpful" AI behavior. Use the guardrail.
