import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CalendarEventRecord


@dataclass
class CalendarEvent:
    id: str
    title: str
    starts_at: datetime
    duration_minutes: int


class CalendarProvider:
    def create_event(self, title: str, starts_at: datetime, duration_minutes: int) -> CalendarEvent:
        raise NotImplementedError

    def list_events(self) -> list[CalendarEvent]:
        raise NotImplementedError


class MockCalendarProvider(CalendarProvider):
    def __init__(self):
        self.events: list[CalendarEvent] = []

    def create_event(self, title: str, starts_at: datetime, duration_minutes: int) -> CalendarEvent:
        if duration_minutes <= 0:
            raise ValueError("Event duration must be positive")
        event = CalendarEvent(str(len(self.events) + 1), title, starts_at, duration_minutes)
        self.events.append(event)
        return event

    def list_events(self) -> list[CalendarEvent]:
        return list(self.events)

    def serialize(self) -> list[dict]:
        return [asdict(event) for event in self.events]


class DatabaseCalendarProvider(CalendarProvider):
    """Persistent, user-scoped mock calendar with the replaceable provider contract."""

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create_event(self, title: str, starts_at: datetime, duration_minutes: int) -> CalendarEvent:
        if not title.strip():
            raise ValueError("Event title is required")
        if duration_minutes <= 0 or duration_minutes > 1440:
            raise ValueError("Event duration must be between 1 and 1440 minutes")
        row = CalendarEventRecord(
            user_id=self.user_id,
            title=title.strip(),
            starts_at=starts_at,
            duration_minutes=duration_minutes,
        )
        self.db.add(row)
        self.db.flush()
        return CalendarEvent(row.id, row.title, row.starts_at, row.duration_minutes)

    def list_events(self) -> list[CalendarEvent]:
        rows = self.db.scalars(
            select(CalendarEventRecord)
            .where(CalendarEventRecord.user_id == self.user_id)
            .order_by(CalendarEventRecord.starts_at)
        ).all()
        return [CalendarEvent(row.id, row.title, row.starts_at, row.duration_minutes) for row in rows]


def parse_calendar_request(question: str, now: datetime | None = None) -> dict:
    """Parse the intentionally bounded MVP calendar command grammar."""
    now = now or datetime.now(UTC)
    text = " ".join(question.strip().split())
    lowered = text.lower()
    if lowered.startswith("list") or "show my calendar" in lowered:
        return {"operation": "list"}
    day = now.date()
    if "tomorrow" in lowered:
        day += timedelta(days=1)
    elif match := re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", lowered):
        day = date.fromisoformat(match.group(1))
    else:
        raise ValueError("Include 'tomorrow' or an ISO date (YYYY-MM-DD) for the event")
    clock = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lowered)
    hour, minute = 19, 0
    if clock:
        hour, minute = int(clock.group(1)), int(clock.group(2) or 0)
        marker = clock.group(3)
        if marker == "pm" and hour < 12:
            hour += 12
        elif marker == "am" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59:
            raise ValueError("The event time is invalid")
    duration_match = re.search(r"(?:for\s+)?(\d+)\s*(minutes?|mins?|hours?|hrs?)", lowered)
    duration = 60
    if duration_match:
        duration = int(duration_match.group(1))
        if duration_match.group(2).startswith(("hour", "hr")):
            duration *= 60
    title = re.sub(r"^(schedule|add|create)(?:\s+an?\s+event)?\s*", "", text, flags=re.IGNORECASE)
    title = re.split(r"\s+(?:tomorrow|on\s+20\d{2}-\d{2}-\d{2})\b", title, maxsplit=1, flags=re.IGNORECASE)[0]
    title = title.strip(" .") or "Study session"
    starts_at = datetime.combine(day, time(hour, minute), tzinfo=UTC)
    return {
        "operation": "create",
        "title": title,
        "starts_at": starts_at,
        "duration_minutes": duration,
    }
