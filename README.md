# SmartMate — AI-Agent Personal Assistant

> Architected a stateful multi-agent system using **LangGraph**, **FastAPI**, and **MCP**,
> integrating Google Calendar and note-taking tools via asynchronous event handling
> to automate complex scheduling workflows over **Slack**.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=flat&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1-FF6B35?style=flat)
![MCP](https://img.shields.io/badge/MCP-1.26-6C3483?style=flat)
![Slack](https://img.shields.io/badge/Slack-Bolt-4A154B?style=flat&logo=slack&logoColor=white)
![Google Calendar](https://img.shields.io/badge/Google_Calendar-API_v3-4285F4?style=flat&logo=google&logoColor=white)

---

## Demo

| Slack Bot Live | Event Subscriptions Verified | Google Calendar Connected |
|---|---|---|
| ![Slack Demo](screenshots/Screenshot%202026-03-14%20232323.png) | ![Slack Events](screenshots/Screenshot%202026-03-14%20232405.png) | ![Google Auth](screenshots/Screenshot%202026-03-14%20232434.png) |

---

## What It Does

SmartMate is a fully functional AI personal assistant that lives in Slack. Send it a natural language message and it autonomously decides what to do — schedule meetings, find free time, or manage your notes — then executes the task end-to-end.

**Example interactions:**
```
You:        "Show my upcoming events"
SmartMate:  Lists your next 10 Google Calendar events

You:        "Find a free hour tomorrow afternoon"
SmartMate:  Queries your calendar, computes free slots, returns available windows

You:        "Create a team sync on Friday at 2pm"
SmartMate:  Creates the event and confirms with a calendar link

You:        "Save a note: project ideas for recommendation engine"
SmartMate:  Stores it in the notes database with timestamp and tags

You:        "Search my notes for recommendation"
SmartMate:  Returns all matching notes with full-text search
```

---

## System Architecture

```
Slack DM / @mention
        │
        ▼
┌──────────────────────────────┐
│      FastAPI Server          │  POST /slack/events
│      (Slack Bolt webhook)    │  GET  /auth/google/login
└──────────────┬───────────────┘  GET  /auth/google/callback
               │ async invoke
               ▼
┌──────────────────────────────────────────────────────┐
│                LangGraph Agent Graph                 │
│                                                      │
│   START                                              │
│     │                                                │
│     ▼                                                │
│  ┌──────────────────┐                                │
│  │  Supervisor Node │  ← GPT-4o class intent         │
│  │  (intent router) │    via structured JSON output  │
│  └────────┬─────────┘                                │
│           │                                          │
│     ┌─────┴──────┬──────────────┐                   │
│     ▼            ▼              ▼                    │
│  [Calendar]   [Notes]       [Responder]              │
│   Agent        Agent          Node                   │
│     │            │                                   │
│  MCP Tool    MCP Tool                                │
│  Server      Server                                  │
│     │            │                                   │
│  Google      SQLite DB                               │
│  Calendar    (aiosqlite)                             │
│  API v3                                              │
│                                                      │
│  MemorySaver checkpointer — stateful per Slack user  │
└──────────────────────────────────────────────────────┘
               │
               ▼
     Slack reply (chat.update)
```

### How the Multi-Agent Routing Works

1. **Slack** sends a webhook POST to the FastAPI server
2. The **Supervisor Agent** (LLM with structured JSON output) classifies intent into one of: `calendar_agent`, `notes_agent`, or `respond`
3. LangGraph routes to the appropriate **sub-agent node**
4. Sub-agents run a **ReAct loop** — reasoning + tool calls — until they have a complete answer
5. Tools are exposed as **MCP servers** (Model Context Protocol), the emerging industry standard for agent tool interfaces
6. The final response is posted back to Slack via `chat.update`, replacing a "thinking..." placeholder

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over LangChain AgentExecutor** | Explicit state graph gives full control over routing, retries, and multi-agent coordination |
| **MCP for tool servers** | Standardized protocol lets agents discover tools dynamically; decouples tools from agent logic |
| **Supervisor + specialist agents** | Separation of concerns — routing logic stays clean, each agent is focused and testable |
| **MemorySaver checkpointer** | Conversations are stateful per Slack user ID — SmartMate remembers context across messages |
| **Slack placeholder pattern** | Immediately posts "thinking..." then updates it, avoiding Slack's 3-second timeout |
| **PKCE OAuth flow** | Implements full OAuth 2.0 PKCE for Google Calendar, persisting flow state between redirect steps |

---

## Tech Stack

| Technology | Role |
|---|---|
| **FastAPI** | Async HTTP server, Slack webhook receiver, OAuth endpoints |
| **LangGraph** | Stateful multi-agent graph orchestration with checkpointing |
| **LangChain** | LLM abstraction, ReAct agent pattern, tool binding |
| **Llama 3.3 70B (Groq)** | LLM backbone — fast inference via Groq's free API |
| **MCP (Model Context Protocol)** | Standardized tool server protocol for agent-tool communication |
| **Slack Bolt** | Event subscription, webhook verification, message posting |
| **Google Calendar API v3** | Create, read, and query calendar events |
| **Google OAuth 2.0 + PKCE** | Secure delegated calendar access with token refresh |
| **aiosqlite** | Async SQLite for persistent note storage |
| **Pydantic / pydantic-settings** | Config validation, type safety, `.env` management |

---

## Project Structure

```
smartmate/
├── main.py                     # FastAPI entry point — server, OAuth routes, Slack webhook
├── config.py                   # Pydantic settings (reads from .env)
├── requirements.txt
├── .env.example                # Environment variable template
│
├── agents/
│   ├── graph.py                # LangGraph graph — nodes, edges, checkpointer
│   ├── supervisor.py           # Supervisor node — JSON-structured intent classification
│   ├── calendar_agent.py       # ReAct agent — Google Calendar tool calls
│   ├── notes_agent.py          # ReAct agent — Notes CRUD tool calls
│   └── responder.py            # Direct LLM response for general conversation
│
├── mcp_servers/
│   ├── calendar_server.py      # MCP server: exposes 4 calendar tools
│   └── notes_server.py         # MCP server: exposes 4 notes tools
│
├── tools/
│   ├── google_calendar.py      # Google Calendar API wrapper (list, create, free slots, delete)
│   └── notes.py                # Async SQLite note storage (create, search, list, delete)
│
├── slack/
│   ├── bot.py                  # Slack Bolt app + message/mention event subscriptions
│   └── handlers.py             # Async message handler — placeholder → agent → update
│
├── auth/
│   └── google_oauth.py         # Google OAuth 2.0 PKCE flow with token persistence
│
└── state/
    └── schemas.py              # AgentState TypedDict — shared state across all graph nodes
```

---

## Setup & Running Locally

### Prerequisites
- Python 3.11+
- A Google account (for Calendar API)
- A Slack workspace
- [ngrok](https://ngrok.com) (for local webhook tunneling)
- A free [Groq API key](https://console.groq.com) (for the LLM)

### 1. Clone & Install

```bash
git clone https://github.com/jwalith/SmartMate.git
cd SmartMate

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Fill in your `.env`:

```env
GROQ_API_KEY=gsk_...                         # From console.groq.com (free)
SLACK_BOT_TOKEN=xoxb-...                     # From api.slack.com/apps → OAuth & Permissions
SLACK_SIGNING_SECRET=...                     # From api.slack.com/apps → Basic Information
GOOGLE_CREDENTIALS_FILE=credentials.json    # Downloaded from GCP Console
GOOGLE_TOKEN_FILE=token.json
PUBLIC_URL=https://your-ngrok-url.ngrok.io  # From ngrok http 8000
OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### 3. Google Cloud Setup (one-time)
1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Google Calendar API**
3. Create **OAuth 2.0 credentials** (Web application type)
4. Add `http://localhost:8000/auth/google/callback` as authorized redirect URI
5. Download `credentials.json` → place in project root
6. Add your Gmail to **OAuth consent screen → Test users**

### 4. Slack App Setup (one-time)
1. Create app at [api.slack.com/apps](https://api.slack.com/apps)
2. Add bot scopes: `chat:write`, `im:history`, `im:read`, `im:write`, `app_mentions:read`
3. Install to workspace → copy `xoxb-` token
4. Enable **Event Subscriptions** → subscribe to `message.im`, `app_mention`
5. Enable DMs in **App Home → Messages Tab**

### 5. Run

```bash
# Terminal 1 — start the server
python main.py

# Terminal 2 — expose to internet
ngrok http 8000

# Browser — authorize Google Calendar (one-time)
open http://localhost:8000/auth/google/login
```

Then DM your bot in Slack.

---

## MCP Servers (Standalone)

Each MCP server can be run and tested independently:

```bash
python -m mcp_servers.calendar_server
python -m mcp_servers.notes_server
```

Tools exposed:

| Server | Tools |
|---|---|
| `calendar_server` | `list_upcoming_events`, `create_event`, `find_free_slots`, `delete_event` |
| `notes_server` | `create_note`, `search_notes`, `list_notes`, `delete_note` |

---


