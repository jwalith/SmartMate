"""
MCP Server: Web Search

Exposes Tavily web search as an MCP tool so LangGraph agents
can search the internet in real time.

Run standalone with:  python -m mcp_servers.search_server
"""

import asyncio
import json
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from tavily import TavilyClient

app = Server("smartmate-search")


def _client() -> TavilyClient:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not set in environment.")
    return TavilyClient(api_key=api_key)


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="web_search",
            description=(
                "Search the web for real-time information. Use this for current events, "
                "weather, news, research questions, or anything that requires up-to-date "
                "information not available in the model's training data."
            ),
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5).",
                        "default": 5,
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "description": "Search depth. Use 'advanced' for complex research questions.",
                        "default": "basic",
                    },
                },
            },
        ),
        types.Tool(
            name="get_webpage",
            description="Fetch and read the full content of a specific webpage URL.",
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch content from.",
                    }
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        client = _client()

        if name == "web_search":
            response = client.search(
                query=arguments["query"],
                max_results=arguments.get("max_results", 5),
                search_depth=arguments.get("search_depth", "basic"),
            )
            results = [
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": r.get("content"),
                    "score": r.get("score"),
                }
                for r in response.get("results", [])
            ]
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "get_webpage":
            content = client.extract(urls=[arguments["url"]])
            return [types.TextContent(type="text", text=json.dumps(content, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
