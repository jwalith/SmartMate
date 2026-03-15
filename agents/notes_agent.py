"""
Notes Agent Node

A ReAct-style agent that has access to all note-taking tools.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from state.schemas import AgentState
from config import get_settings
from tools.notes import create_note, search_notes, list_notes, delete_note
import asyncio
import json

SYSTEM_PROMPT = """You are SmartMate's Notes Agent. You help users create, search, and manage their personal notes.

You have tools to:
- Create new notes with a title, content, and optional tags
- Search notes by keyword
- List recent notes
- Delete notes by ID

Always confirm what you did in a friendly, concise Slack message.
Use bullet points for lists of notes. Keep it readable in Slack (no markdown headers).
"""


def _run_async(coro):
    """Run an async function synchronously (LangChain tools are sync)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@tool
def tool_create_note(title: str, content: str, tags: list[str] | None = None) -> str:
    """Create and save a new note."""
    note = _run_async(create_note(title, content, tags))
    return json.dumps(note, indent=2)


@tool
def tool_search_notes(query: str) -> str:
    """Search notes by keyword across title, content, and tags."""
    notes = _run_async(search_notes(query))
    return json.dumps(notes, indent=2)


@tool
def tool_list_notes(limit: int = 10) -> str:
    """List the most recently updated notes."""
    notes = _run_async(list_notes(limit))
    return json.dumps(notes, indent=2)


@tool
def tool_delete_note(note_id: int) -> str:
    """Delete a note by its numeric ID."""
    result = _run_async(delete_note(note_id))
    return json.dumps({"deleted": result})


NOTES_TOOLS = [tool_create_note, tool_search_notes, tool_list_notes, tool_delete_note]
TOOL_MAP = {t.name: t for t in NOTES_TOOLS}


def notes_agent_node(state: AgentState) -> AgentState:
    """ReAct loop for notes operations."""
    settings = get_settings()
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.groq_api_key,
    ).bind_tools(NOTES_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
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
        "notes_result": final_response,
        "final_response": final_response,
    }
