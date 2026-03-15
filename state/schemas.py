from typing import Annotated, Literal
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state passed between all nodes in the LangGraph graph."""

    # Full conversation history — add_messages handles merging new messages
    messages: Annotated[list[AnyMessage], add_messages]

    # Slack context
    slack_user_id: str
    slack_channel_id: str
    slack_thread_ts: str | None

    # Routing decision made by the supervisor
    next_agent: Literal["calendar_agent", "notes_agent", "search_agent", "respond", "__end__"] | None

    # Structured outputs from sub-agents (cleared each turn)
    calendar_result: str | None
    notes_result: str | None
    search_result: str | None

    # Final response to send back to Slack
    final_response: str | None
