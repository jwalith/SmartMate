"""
Responder Node

Handles general conversation (greetings, capability questions, chitchat).
No tools needed — just a direct LLM response.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from state.schemas import AgentState
from config import get_settings

SYSTEM_PROMPT = """You are SmartMate, a friendly AI personal assistant living in Slack.

You help users with:
• 📅 Google Calendar — create events, find free time, list upcoming meetings
• 📝 Notes — save, search, and manage personal notes

Keep your responses brief and conversational. Use Slack-friendly formatting.
If the user asks what you can do, give a short bulleted list of capabilities.
"""


def responder_node(state: AgentState) -> AgentState:
    """Generate a direct conversational response (no tools)."""
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
    return {**state, "final_response": response.content}
