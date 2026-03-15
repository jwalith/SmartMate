"""
SmartMate LangGraph Agent Graph

Topology:
  START → supervisor → [calendar_agent | notes_agent | respond] → END

State is checkpointed per (slack_user_id, thread) so conversations
are stateful across multiple Slack messages.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state.schemas import AgentState
from agents.supervisor import supervisor_node, route_after_supervisor
from agents.calendar_agent import calendar_agent_node
from agents.notes_agent import notes_agent_node
from agents.search_agent import search_agent_node
from agents.responder import responder_node

# ── Build graph ──────────────────────────────────────────────────────────────

builder = StateGraph(AgentState)

# Nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("calendar_agent", calendar_agent_node)
builder.add_node("notes_agent", notes_agent_node)
builder.add_node("search_agent", search_agent_node)
builder.add_node("respond", responder_node)

# Edges
builder.add_edge(START, "supervisor")

builder.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "calendar_agent": "calendar_agent",
        "notes_agent": "notes_agent",
        "search_agent": "search_agent",
        "respond": "respond",
    },
)

builder.add_edge("calendar_agent", END)
builder.add_edge("notes_agent", END)
builder.add_edge("search_agent", END)
builder.add_edge("respond", END)

# In-memory checkpointer (persists state across turns within the same process).
# For production swap with SqliteSaver or RedisSaver.
checkpointer = MemorySaver()

graph = builder.compile(checkpointer=checkpointer)


# ── Public helper ────────────────────────────────────────────────────────────

async def run_agent(
    user_message: str,
    slack_user_id: str,
    slack_channel_id: str,
    slack_thread_ts: str | None = None,
) -> str:
    """
    Run the agent graph for one user turn.

    Args:
        user_message:     The raw text from Slack.
        slack_user_id:    Slack user ID (e.g. U01234ABC).
        slack_channel_id: Slack channel/DM ID.
        slack_thread_ts:  Thread timestamp if replying in-thread.

    Returns:
        The agent's final response text to send back to Slack.
    """
    from langchain_core.messages import HumanMessage

    # Use user_id as the thread key so each user has their own persistent state
    config = {"configurable": {"thread_id": slack_user_id}}

    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "slack_user_id": slack_user_id,
        "slack_channel_id": slack_channel_id,
        "slack_thread_ts": slack_thread_ts,
        "next_agent": None,
        "calendar_result": None,
        "notes_result": None,
        "search_result": None,
        "final_response": None,
    }

    result = await graph.ainvoke(initial_state, config=config)
    return result.get("final_response") or "Sorry, I couldn't process that. Please try again."
