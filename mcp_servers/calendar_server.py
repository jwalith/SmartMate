"""
MCP Server: Google Calendar

Exposes calendar operations as MCP tools so LangGraph agents
can discover and call them via the standardized MCP protocol.

Run standalone with:  python -m mcp_servers.calendar_server
"""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from tools.google_calendar import (
    list_upcoming_events,
    create_event,
    find_free_slots,
    delete_event,
)

app = Server("smartmate-calendar")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_upcoming_events",
            description="List the next N upcoming events on the user's Google Calendar.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return (default 10).",
                        "default": 10,
                    }
                },
            },
        ),
        types.Tool(
            name="create_event",
            description="Create a new event on the user's Google Calendar.",
            inputSchema={
                "type": "object",
                "required": ["summary", "start_datetime", "end_datetime"],
                "properties": {
                    "summary": {"type": "string", "description": "Event title."},
                    "start_datetime": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format, e.g. 2026-03-15T10:00:00Z",
                    },
                    "end_datetime": {
                        "type": "string",
                        "description": "End time in ISO 8601 format.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional event description.",
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee email addresses.",
                    },
                },
            },
        ),
        types.Tool(
            name="find_free_slots",
            description="Find available time slots on a given date.",
            inputSchema={
                "type": "object",
                "required": ["date"],
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format.",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Required slot length in minutes (default 60).",
                        "default": 60,
                    },
                    "working_hours_start": {
                        "type": "integer",
                        "description": "Start of working day in 24h format (default 9).",
                        "default": 9,
                    },
                    "working_hours_end": {
                        "type": "integer",
                        "description": "End of working day in 24h format (default 17).",
                        "default": 17,
                    },
                },
            },
        ),
        types.Tool(
            name="delete_event",
            description="Delete a calendar event by its ID.",
            inputSchema={
                "type": "object",
                "required": ["event_id"],
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The Google Calendar event ID.",
                    }
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "list_upcoming_events":
            result = list_upcoming_events(arguments.get("max_results", 10))
        elif name == "create_event":
            result = create_event(**arguments)
        elif name == "find_free_slots":
            result = find_free_slots(**arguments)
        elif name == "delete_event":
            result = delete_event(arguments["event_id"])
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
