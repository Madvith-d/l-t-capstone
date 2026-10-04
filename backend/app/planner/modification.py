import re
from copy import deepcopy
from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel

from app.planner.engine import PlanValidationError, validate_sessions

DAYS = {
    name.lower(): index
    for index, name in enumerate(
        ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    )
}


class ModificationOperation(str, Enum):
    REMOVE_DAY = "REMOVE_DAY"
    MOVE_SESSIONS = "MOVE_SESSIONS"
    LIMIT_DAY = "LIMIT_DAY"
    RESCHEDULE = "RESCHEDULE"


class ModificationCommand(BaseModel):
    operation: ModificationOperation
    subject: str | None = None
    target_date: date | None = None
    weekday: int | None = None
    limit_minutes: int | None = None
    scope: str = "one"


def next_weekday(day: date, weekday: int) -> date:
    return day + timedelta(days=(weekday - day.weekday()) % 7 or 7)


def parse_modification(
    instruction: str,
    subjects: list[dict],
    today: date | None = None,
) -> ModificationCommand:
    text = instruction.strip().lower()
    today = today or date.today()
    subject = next((item["name"] for item in subjects if item["name"].lower() in text), None)
    forbidden = next(
        (
            number
            for name, number in DAYS.items()
            if f"no {name}" in text
            or f"cannot study on {name}" in text
            or f"can't study on {name}" in text
            or f"remove {name}" in text
        ),
        None,
    )
    if forbidden is not None:
        return ModificationCommand(
            operation=ModificationOperation.REMOVE_DAY,
            weekday=forbidden,
            scope="all",
        )

    hours = re.search(r"(?:only have|limit(?:.*?to)?)\s+(\d+(?:\.\d+)?)\s*hour", text)
    if hours and "tomorrow" in text:
        return ModificationCommand(
            operation=ModificationOperation.LIMIT_DAY,
            target_date=today + timedelta(days=1),
            limit_minutes=int(float(hours.group(1)) * 60),
            scope="day",
        )

    target_day = next(
        (number for name, number in DAYS.items() if f"to {name}" in text),
        None,
    )
    iso_date = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if subject and (target_day is not None or iso_date):
        target = (
            date.fromisoformat(iso_date.group(1))
            if iso_date
            else next_weekday(today - timedelta(days=1), target_day)  # type: ignore[arg-type]
        )
        scope = "all" if re.search(r"\b(all|every)\b", text) else "one"
        return ModificationCommand(
            operation=ModificationOperation.MOVE_SESSIONS,
            subject=subject,
            target_date=target,
            scope=scope,
        )

    raise PlanValidationError(
        [
            (
                "Use an unavailable weekday, a daily-hour limit, or move a named subject "
                "to a weekday/date. Say 'all' explicitly to move every matching session."
            )
        ]
    )


def _redistribute(
    updated: list[dict],
    displaced: list[dict],
    exam_date: date,
    daily_hours: float,
    today: date,
    forbidden_weekday: int | None = None,
) -> None:
    daily_limit = int(daily_hours * 60)
    for item in displaced:
        placed = False
        start = max(today, item["session_date"])
        for offset in range(max(1, (exam_date - start).days)):
            candidate = start + timedelta(days=offset)
            if candidate >= exam_date or candidate.weekday() == forbidden_weekday:
                continue
            used = sum(
                entry["duration_minutes"]
                for entry in updated
                if entry["session_date"] == candidate
            )
            if used + item["duration_minutes"] <= daily_limit:
                item["session_date"] = candidate
                updated.append(item)
                placed = True
                break
        if not placed:
            raise PlanValidationError(["The displaced workload cannot fit before the exam"])


def apply_modification(
    sessions: list[dict],
    command: ModificationCommand,
    subjects: list[dict],
    exam_date: date,
    daily_hours: float,
    today: date | None = None,
) -> list[dict]:
    updated = deepcopy(sessions)
    today = today or date.today()
    displaced: list[dict] = []

    if command.operation == ModificationOperation.REMOVE_DAY:
        displaced = [
            item for item in updated if item["session_date"].weekday() == command.weekday
        ]
        updated = [
            item for item in updated if item["session_date"].weekday() != command.weekday
        ]
        _redistribute(updated, displaced, exam_date, daily_hours, today, command.weekday)
    elif command.operation == ModificationOperation.LIMIT_DAY:
        day_sessions = sorted(
            [item for item in updated if item["session_date"] == command.target_date],
            key=lambda item: (-item["duration_minutes"], item["subject"], item["topic"]),
        )
        kept_minutes = 0
        for item in day_sessions:
            if kept_minutes + item["duration_minutes"] <= (command.limit_minutes or 0):
                kept_minutes += item["duration_minutes"]
            else:
                updated.remove(item)
                displaced.append(item)
        _redistribute(updated, displaced, exam_date, daily_hours, today)
    elif command.operation == ModificationOperation.MOVE_SESSIONS:
        affected = [item for item in updated if item["subject"] == command.subject]
        if not affected:
            raise PlanValidationError([f"No sessions found for {command.subject}"])
        if command.scope != "all":
            affected = [min(affected, key=lambda item: item["session_date"])]
        destination = command.target_date
        if destination is None or destination >= exam_date:
            raise PlanValidationError(["The destination must be before the examination date"])
        used = sum(
            item["duration_minutes"]
            for item in updated
            if item["session_date"] == destination and item not in affected
        )
        if used + sum(item["duration_minutes"] for item in affected) > daily_hours * 60:
            raise PlanValidationError(["The destination day does not have enough free time"])
        for item in affected:
            item["session_date"] = destination
    else:
        raise PlanValidationError(["Unsupported plan modification"])

    errors = validate_sessions(updated, subjects, exam_date, daily_hours)
    if errors:
        raise PlanValidationError(errors)
    return sorted(updated, key=lambda item: (item["session_date"], item["subject"], item["topic"]))


def modify_sessions(
    sessions: list[dict],
    instruction: str,
    subjects: list[dict],
    exam_date: date,
    daily_hours: float,
    today: date | None = None,
) -> list[dict]:
    command = parse_modification(instruction, subjects, today)
    return apply_modification(sessions, command, subjects, exam_date, daily_hours, today)
