"""
Supervisor Agent Node

Reads the latest user message and decides which sub-agent to route to,
or whether to respond directly.
Uses structured output (JSON) for deterministic routing.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state.schemas import AgentState
from config import get_settings

SYSTEM_PROMPT = """You are SmartMate, a personal AI assistant that lives in Slack.
You help users manage their Google Calendar, personal notes, and can search the web.

Your job right now is to classify the user's intent and route to the right agent.

Respond ONLY with valid JSON in this exact format:
{
  "next_agent": "<one of: calendar_agent | notes_agent | search_agent | respond>",
  "reasoning": "<one sentence explanation>"
}

Routing rules:
- "calendar_agent"  → anything about scheduling, events, meetings, free time, calendar
- "notes_agent"     → anything about notes, reminders, saving info, searching past notes
- "search_agent"    → anything requiring real-time or external information: news, weather,
                      current events, research questions, definitions, comparisons,
                      or anything the model cannot know from training data alone
- "respond"         → greetings, questions about what you can do, or chitchat
"""


def supervisor_node(state: AgentState) -> AgentState:
    """Classify intent and set next_agent in state."""
    settings = get_settings()
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.groq_api_key,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *state["messages"],
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    import json
    try:
        parsed = json.loads(content)
        next_agent = parsed.get("next_agent", "respond")
    except (json.JSONDecodeError, KeyError):
        next_agent = "respond"

    return {**state, "next_agent": next_agent}


def route_after_supervisor(state: AgentState) -> str:
    """Edge function: return the next node name based on supervisor's decision."""
    agent = state.get("next_agent", "respond")
    # Fallback to respond if unknown routing value
    if agent not in ("calendar_agent", "notes_agent", "search_agent", "respond"):
        return "respond"
    return agent
