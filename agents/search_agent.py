"""
Search Agent Node

Directly calls Tavily for web search (no LLM tool calling),
then uses the LLM to synthesize a clean answer from the results.
This avoids Groq/Llama tool-call format incompatibilities entirely.
"""

import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from state.schemas import AgentState
from config import get_settings
from tavily import TavilyClient


def _search(query: str, max_results: int = 5) -> list[dict]:
    settings = get_settings()
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env file.")
    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(query=query, max_results=max_results, search_depth="basic")
    return [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
        }
        for r in response.get("results", [])
    ]


def _extract_query(state: AgentState) -> str:
    """Pull the latest human message text from state."""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "human":
            return msg.content
    return ""


def search_agent_node(state: AgentState) -> AgentState:
    """
    1. Extract user query from state
    2. Call Tavily directly (no LLM tool calling)
    3. Pass search results to LLM to synthesize a clean answer
    """
    settings = get_settings()
    user_query = _extract_query(state)

    try:
        results = _search(user_query)
        results_text = json.dumps(results, indent=2)
    except Exception as e:
        final_response = f"Sorry, I couldn't search the web right now: `{str(e)}`"
        return {**state, "search_result": final_response, "final_response": final_response}

    from datetime import date
    today = date.today().isoformat()

    synthesis_prompt = f"""You are SmartMate's Search Agent. Today is {today}.

The user asked: "{user_query}"

Here are the web search results:
{results_text}

Synthesize a clear, concise answer based on these results.
- Use bullet points where helpful
- Include source URLs for key facts
- Keep it Slack-friendly (no markdown headers, short paragraphs)
- If results don't fully answer the question, say so honestly
"""

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.groq_api_key,
    )

    response = llm.invoke([HumanMessage(content=synthesis_prompt)])
    final_response = response.content

    return {
        **state,
        "search_result": final_response,
        "final_response": final_response,
    }
