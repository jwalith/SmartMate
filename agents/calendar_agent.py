"""
Calendar Agent Node

A ReAct-style agent that has access to all Google Calendar tools.
It reasons step-by-step and calls tools until it has a final answer.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from state.schemas import AgentState
from config import get_settings
from tools.google_calendar import (
    list_upcoming_events,
    create_event,
    find_free_slots,
    delete_event,
)
import json

SYSTEM_PROMPT = """You are SmartMate's Calendar Agent. You help users manage their Google Calendar.

You have tools to:
- List upcoming events
- Create new events
- Find free time slots on a given day
- Delete events

Always confirm what you did in a friendly, concise Slack message.
Use bullet points or bold text for clarity. Do not include markdown headers.

Today's date context will be provided in the conversation.
"""


@tool
def tool_list_upcoming_events(max_results: int = 10) -> str:
    """List the next upcoming events on the user's Google Calendar."""
    events = list_upcoming_events(max_results)
    return json.dumps(events, indent=2)


@tool
def tool_create_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    attendees: list[str] | None = None,
) -> str:
    """Create a new event on the user's Google Calendar."""
    event = create_event(summary, start_datetime, end_datetime, description, attendees)
    return json.dumps(event, indent=2)


@tool
def tool_find_free_slots(
    date: str,
    duration_minutes: int = 60,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
) -> str:
    """Find available time slots on a given date."""
    slots = find_free_slots(date, duration_minutes, working_hours_start, working_hours_end)
    return json.dumps(slots, indent=2)


@tool
def tool_delete_event(event_id: str) -> str:
    """Delete a calendar event by its ID."""
    result = delete_event(event_id)
    return json.dumps({"deleted": result})


CALENDAR_TOOLS = [
    tool_list_upcoming_events,
    tool_create_event,
    tool_find_free_slots,
    tool_delete_event,
]

TOOL_MAP = {t.name: t for t in CALENDAR_TOOLS}


def calendar_agent_node(state: AgentState) -> AgentState:
    """ReAct loop: reason → call tools → reason → … → final answer."""
    settings = get_settings()
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.groq_api_key,
    ).bind_tools(CALENDAR_TOOLS)

    from datetime import date
    today = date.today().isoformat()

    messages = [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\nToday's date: {today}"),
        *state["messages"],
    ]

    while True:
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            fn = TOOL_MAP.get(tc["name"])
            if fn:
                result = fn.invoke(tc["args"])
            else:
                result = f"Unknown tool: {tc['name']}"
            messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )

    final_response = response.content if isinstance(response, AIMessage) else str(response)

    return {
        **state,
        "calendar_result": final_response,
        "final_response": final_response,
    }
