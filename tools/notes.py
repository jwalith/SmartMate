"""
SQLite-backed note storage.
All operations are async (aiosqlite).
"""

import aiosqlite
from datetime import datetime, timezone
from config import get_settings


def _db_path() -> str:
    return get_settings().notes_db_path


async def init_db() -> None:
    """Create the notes table if it doesn't exist. Call on app startup."""
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                content    TEXT NOT NULL,
                tags       TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def create_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    """Insert a new note and return it."""
    now = datetime.now(timezone.utc).isoformat()
    tags_str = ",".join(tags or [])
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO notes (title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (title, content, tags_str, now, now),
        )
        await db.commit()
        note_id = cursor.lastrowid
        async with db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row)


async def get_note(note_id: int) -> dict | None:
    """Fetch a single note by ID."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)) as cur:
            row = await cur.fetchone()
    return _row_to_dict(row) if row else None


async def search_notes(query: str) -> list[dict]:
    """Full-text search across title, content, and tags."""
    like = f"%{query}%"
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? ORDER BY updated_at DESC",
            (like, like, like),
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def list_notes(limit: int = 10) -> list[dict]:
    """Return the most recently updated notes."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
    return [_row_to_dict(r) for r in rows]


async def delete_note(note_id: int) -> bool:
    """Delete a note by ID."""
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        await db.commit()
    return True


def _row_to_dict(row: aiosqlite.Row) -> dict:
    d = dict(row)
    d["tags"] = d["tags"].split(",") if d["tags"] else []
    return d
