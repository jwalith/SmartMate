"""
Google Calendar API wrapper.
All functions are synchronous (Google client lib is sync).
Agent nodes call these directly.
"""

from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from auth.google_oauth import get_credentials


def _service():
    creds = get_credentials()
    if not creds:
        raise RuntimeError(
            "Google Calendar not authorized. Visit /auth/google/login first."
        )
    return build("calendar", "v3", credentials=creds)


def list_upcoming_events(max_results: int = 10) -> list[dict]:
    """Return the next N events from the primary calendar."""
    now = datetime.now(timezone.utc).isoformat()
    events_result = (
        _service()
        .events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    items = events_result.get("items", [])
    return [_format_event(e) for e in items]


def create_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    attendees: list[str] | None = None,
) -> dict:
    """
    Create a calendar event.

    Args:
        summary: Event title.
        start_datetime: ISO 8601 string, e.g. "2026-03-15T10:00:00-05:00"
        end_datetime:   ISO 8601 string, e.g. "2026-03-15T11:00:00-05:00"
        description:    Optional event description.
        attendees:      List of email addresses to invite.
    """
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": "UTC"},
        "end": {"dateTime": end_datetime, "timeZone": "UTC"},
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]

    event = _service().events().insert(calendarId="primary", body=body).execute()
    return _format_event(event)


def find_free_slots(
    date: str,
    duration_minutes: int = 60,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
) -> list[dict]:
    """
    Find free time slots on a given date.

    Args:
        date: "YYYY-MM-DD"
        duration_minutes: How long the slot needs to be.
        working_hours_start: Start of working day (24h).
        working_hours_end: End of working day (24h).
    """
    day_start = datetime.fromisoformat(f"{date}T{working_hours_start:02d}:00:00+00:00")
    day_end = datetime.fromisoformat(f"{date}T{working_hours_end:02d}:00:00+00:00")

    body = {
        "timeMin": day_start.isoformat(),
        "timeMax": day_end.isoformat(),
        "items": [{"id": "primary"}],
    }
    freebusy = _service().freebusy().query(body=body).execute()
    busy_periods = freebusy["calendars"]["primary"]["busy"]

    # Build list of busy intervals
    busy = [
        (
            datetime.fromisoformat(p["start"]),
            datetime.fromisoformat(p["end"]),
        )
        for p in busy_periods
    ]
    busy.sort(key=lambda x: x[0])

    # Walk the working day and collect free slots
    free_slots = []
    cursor = day_start
    slot_delta = timedelta(minutes=duration_minutes)

    for busy_start, busy_end in busy:
        while cursor + slot_delta <= busy_start:
            free_slots.append(
                {
                    "start": cursor.isoformat(),
                    "end": (cursor + slot_delta).isoformat(),
                }
            )
            cursor += slot_delta
        cursor = max(cursor, busy_end)

    while cursor + slot_delta <= day_end:
        free_slots.append(
            {
                "start": cursor.isoformat(),
                "end": (cursor + slot_delta).isoformat(),
            }
        )
        cursor += slot_delta

    return free_slots


def delete_event(event_id: str) -> bool:
    """Delete an event by its ID."""
    _service().events().delete(calendarId="primary", eventId=event_id).execute()
    return True


def _format_event(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event.get("id"),
        "summary": event.get("summary", "(No title)"),
        "start": start.get("dateTime", start.get("date")),
        "end": end.get("dateTime", end.get("date")),
        "description": event.get("description", ""),
        "attendees": [a["email"] for a in event.get("attendees", [])],
        "link": event.get("htmlLink"),
    }
