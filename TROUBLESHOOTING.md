# SmartMate — Build Troubleshooting Log

A record of every issue encountered during the build and how each was resolved.
Useful for interviews, portfolio explanations, and future debugging.

---

## Issue 1 — Dependency Version Conflict on `pip install`

### Error
```
ERROR: Cannot install requirements.txt because these package versions have conflicting dependencies.
The conflict is caused by:
    langchain-groq 0.2.3 requires langchain-core>=0.3.29
    but langchain-core==0.3.28 was pinned
```

### Root Cause
The original `requirements.txt` had hard-pinned exact versions (`==`) for all packages.
`langchain-groq==0.2.3` required `langchain-core>=0.3.29` but we pinned `0.3.28`, causing
pip's dependency resolver to fail.

### Fix
Switched all version pins from exact (`==`) to minimum (`>=`) so pip can resolve
compatible versions automatically:
```
# Before
langchain-core==0.3.28

# After
langchain-core>=0.3.29
```

---

## Issue 2 — `aiosqlite` Crash on Server Startup

### Error
```
RuntimeError: threads can only be started once
RuntimeError: Event loop is closed
```

### Root Cause
The original `tools/notes.py` used a two-step pattern with `aiosqlite`:
```python
db = await aiosqlite.connect(...)   # starts the thread
async with db:                       # tries to start it again → crash
    ...
```
Awaiting the connection AND then using it as an async context manager caused
the internal thread to attempt starting twice, which Python disallows.

### Fix
Switched to using `aiosqlite.connect()` exclusively as an async context manager,
which is the correct pattern in newer versions:
```python
async with aiosqlite.connect(db_path) as db:
    db.row_factory = aiosqlite.Row
    # all operations here
```
Applied this pattern consistently across all functions in `tools/notes.py`.

---

## Issue 3 — Google OAuth: `access_denied` (Error 403)

### Error
```
Access blocked: SmartMate has not completed the Google verification process.
Error 403: access_denied
```

### Root Cause
The GCP OAuth app was in "Testing" mode, which restricts sign-in to a whitelist
of explicitly approved test users. The user's Gmail was not on the list.

### Fix
1. Go to **GCP Console → APIs & Services → OAuth consent screen**
2. Scroll to **Test users**
3. Click **+ Add Users** → add `jwalithkristam@gmail.com`
4. Save

---

## Issue 4 — Google OAuth: `invalid_grant` / Missing Code Verifier

### Error
```
Error: (invalid_grant) Missing code verifier.
```

### Root Cause
Newer versions of `google-auth-oauthlib` use **PKCE** (Proof Key for Code Exchange)
by default. PKCE generates a `code_verifier` during the `/auth/google/login` step
and requires the same verifier during the `/auth/google/callback` step to exchange
the code for tokens.

The original implementation created a **new** `Flow` object in the callback, which
had no knowledge of the `code_verifier` generated during login. This caused Google
to reject the token exchange.

### Fix
Stored the `Flow` instance in a **module-level variable** between the login and
callback requests, so the same object (with its `code_verifier`) is reused:

```python
# auth/google_oauth.py
_pending_flow: Flow | None = None

def start_auth_flow() -> str:
    global _pending_flow
    _pending_flow = Flow.from_client_secrets_file(...)
    auth_url, _ = _pending_flow.authorization_url(...)
    return auth_url

def complete_auth_flow(code: str) -> Credentials:
    global _pending_flow
    _pending_flow.fetch_token(code=code)   # reuses the same flow with code_verifier
    ...
    _pending_flow = None
```

This is safe for a single-user local app. For multi-user production, the flow state
should be stored in a server-side session keyed by user.

---

## Issue 5 — Google OAuth: `redirect_uri_mismatch` (Error 400)

### Error
```
Error 400: redirect_uri_mismatch
Request details: redirect_uri=https://dionna-exegetic-doggishly.ngrok-free.dev/auth/google/callback
```

### Root Cause
After setting `PUBLIC_URL` to the ngrok URL (required for Slack webhooks), the OAuth
flow started using that ngrok URL as its redirect URI. But GCP only had
`http://localhost:8000/auth/google/callback` registered as an authorized redirect URI.

Google rejects any redirect URI that doesn't exactly match the registered list.

### Fix
Separated the two URLs into distinct config fields:

```env
# .env
PUBLIC_URL=https://dionna-exegetic-doggishly.ngrok-free.dev   # used by Slack
OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback  # used by Google OAuth
```

```python
# config.py
public_url: str = "http://localhost:8000"
oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"
```

The OAuth flow always uses `localhost` because the browser authorization happens
locally. Only Slack webhooks need the public ngrok URL.

Also required a **full server restart** (not just auto-reload) because uvicorn's
file watcher monitors Python files only — `.env` changes are not detected automatically.

---

## Issue 6 — Slack Bot: "Sending messages to this app has been turned off"

### Symptom
The Slack DM input box was greyed out with the message:
> *"Sending messages to this app has been turned off."*

### Root Cause
Slack's **App Home** DM feature was not enabled for the bot. By default, Slack
apps do not allow users to send direct messages to them unless explicitly configured.

### Fix
1. Go to **api.slack.com/apps → SmartMate → App Home**
2. Scroll to **"Show Tabs"**
3. Enable **"Allow users to send Slash commands and messages from the messages tab"**
4. Save

---

---

## Issue 7 — Web Search Agent: `tool_use_failed` / Wrong Tool Call Format

### Error
```
Error code: 400 - {'error': {'message': "Failed to call a function. Please adjust your prompt.",
'type': 'invalid_request_error', 'code': 'tool_use_failed',
'failed_generation': '<function=web_search {"query": "New York weather today", "max_results": 5}</function>'}}
```

### Root Cause
`llama-3.3-70b-versatile` on Groq generates tool calls in the **Hermes XML format**
(`<function=name {...}></function>`) when bound with LangChain's `.bind_tools()`.
Groq's API expects the **OpenAI JSON format** for tool calls and rejects the Hermes format.

Switching to `llama3-groq-70b-8192-tool-use-preview` (Groq's tool-use fine-tuned model)
did not fix it either — that model was subsequently decommissioned (see Issue 8).

### Fix
Eliminated LLM tool calling for the search agent entirely. Instead:
1. **Call Tavily directly** in Python (no LLM involved in the search step)
2. **Pass the raw results to the LLM** for synthesis into a readable answer

```python
# agents/search_agent.py
def search_agent_node(state):
    results = _search(user_query)          # direct Tavily call — no LLM tool call
    response = llm.invoke([HumanMessage(   # LLM only summarizes results
        content=f"Synthesize: {results}"
    )])
```

This pattern is actually architecturally cleaner — search is deterministic (Tavily always
searches), and the LLM's job is reasoning/synthesis, not deciding whether to search.

---

## Issue 8 — Groq Model Decommissioned: `llama3-groq-70b-8192-tool-use-preview`

### Error
```
Error code: 400 - {'error': {'message': "The model `llama3-groq-70b-8192-tool-use-preview`
has been decommissioned and is no longer supported."}}
```

### Root Cause
While debugging the tool call format issue (Issue 7), the calendar and notes agents
were temporarily switched to `llama3-groq-70b-8192-tool-use-preview` — Groq's
tool-use optimized model. Groq decommissioned this model without deprecation notice,
breaking the calendar and notes functionality.

### Fix
Reverted all agents back to `llama-3.3-70b-versatile` which remains active and
handles tool calling correctly for calendar and notes operations:

```python
llm = ChatGroq(
    model="llama-3.3-70b-versatile",   # stable, actively maintained
    temperature=0,
    api_key=settings.groq_api_key,
).bind_tools(TOOLS)
```

**Lesson:** For production systems, pin model versions and monitor provider
deprecation announcements. For portfolio projects, prefer widely-supported
general models over preview/specialized variants.

---

## Issue 9 — LangSmith Traces Not Appearing (Trace Count: 0)

### Symptom
LangSmith dashboard showed the SmartMate project with 0 traces despite the server
running and processing Slack messages successfully.

### Root Cause
LangChain reads tracing configuration (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`,
`LANGCHAIN_PROJECT`) directly from `os.environ`. Pydantic-settings loads `.env` values
into the `Settings` class internally but does **not** inject them into `os.environ`.

As a result, LangChain never saw the tracing vars and silently skipped all tracing.

### Fix
Added `load_dotenv()` at the very top of `main.py`, before any LangChain imports,
so `.env` values are populated into `os.environ` at process startup:

```python
# main.py — must be first, before any langchain imports
from dotenv import load_dotenv
load_dotenv()

import logging
from fastapi import FastAPI
# ... rest of imports
```

---

## Issue 10 — Tavily API Key Not Found at Runtime

### Error
```
SmartMate: Sorry, I couldn't search the web right now: `TAVILY_API_KEY is not set.`
```

### Root Cause
The search agent originally read the Tavily key via `os.getenv("TAVILY_API_KEY")`.
Since `load_dotenv()` had not yet been added (Issue 9), and pydantic-settings doesn't
set OS environment variables, `os.getenv()` returned `None`.

Additionally, the `get_settings()` function uses `@lru_cache` — once the `Settings`
object is created, it's cached for the lifetime of the process. Adding a new field
(`tavily_api_key`) to the `Settings` class requires a full server restart to take
effect; the auto-reloader reloads Python modules but the cached settings object persists.

### Fix
1. Added `tavily_api_key` to the `Settings` class in `config.py`
2. Updated `search_agent.py` to read the key via `get_settings().tavily_api_key`
   instead of `os.getenv()` — consistent with how all other API keys are handled
3. Added `load_dotenv()` to `main.py` (see Issue 9) to ensure all vars are in `os.environ`
4. Full server restart (not auto-reload) required whenever new settings fields are added

---

## Summary Table

| # | Issue | Category | Fix |
|---|---|---|---|
| 1 | pip dependency conflict | Dependencies | Relaxed version pins from `==` to `>=` |
| 2 | aiosqlite thread crash | Async / SQLite | Use `async with aiosqlite.connect()` consistently |
| 3 | Google OAuth access_denied | GCP Setup | Added Gmail to OAuth test users list |
| 4 | Missing code verifier (PKCE) | OAuth / Security | Persisted Flow instance between login and callback |
| 5 | redirect_uri_mismatch | OAuth / Config | Separated `PUBLIC_URL` from `OAUTH_REDIRECT_URI` |
| 6 | Slack DM disabled | Slack Config | Enabled messages tab in App Home settings |
| 7 | LLM tool call format error | Groq / LangChain | Replaced LLM tool calling with direct Tavily API call |
| 8 | Groq model decommissioned | LLM Provider | Reverted to `llama-3.3-70b-versatile` |
| 9 | LangSmith traces not appearing | Observability | Added `load_dotenv()` before LangChain imports |
| 10 | Tavily API key not found at runtime | Config / Cache | Routed key through `get_settings()` + full restart |
