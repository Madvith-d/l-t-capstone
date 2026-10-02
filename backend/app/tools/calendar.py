from dataclasses import asdict, dataclass
from datetime import datetime


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
