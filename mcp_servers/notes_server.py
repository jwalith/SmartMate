"""
MCP Server: Notes

Exposes note-taking operations as MCP tools.

Run standalone with:  python -m mcp_servers.notes_server
"""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from tools.notes import create_note, search_notes, list_notes, delete_note

app = Server("smartmate-notes")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_note",
            description="Create and save a new note with a title, content, and optional tags.",
            inputSchema={
                "type": "object",
                "required": ["title", "content"],
                "properties": {
                    "title": {"type": "string", "description": "Note title."},
                    "content": {"type": "string", "description": "Note body content."},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tags for organization.",
                    },
                },
            },
        ),
        types.Tool(
            name="search_notes",
            description="Search notes by keyword across title, content, and tags.",
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword or phrase.",
                    }
                },
            },
        ),
        types.Tool(
            name="list_notes",
            description="List the most recently updated notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default 10).",
                        "default": 10,
                    }
                },
            },
        ),
        types.Tool(
            name="delete_note",
            description="Delete a note by its ID.",
            inputSchema={
                "type": "object",
                "required": ["note_id"],
                "properties": {
                    "note_id": {
                        "type": "integer",
                        "description": "The note's numeric ID.",
                    }
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "create_note":
            result = await create_note(**arguments)
        elif name == "search_notes":
            result = await search_notes(arguments["query"])
        elif name == "list_notes":
            result = await list_notes(arguments.get("limit", 10))
        elif name == "delete_note":
            result = await delete_note(arguments["note_id"])
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
