import re
from copy import deepcopy
from datetime import date, timedelta

from app.planner.engine import PlanValidationError, validate_sessions

DAYS = {
    name.lower(): index
    for index, name in enumerate(
        ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    )
}


def next_weekday(day: date, weekday: int) -> date:
    return day + timedelta(days=(weekday - day.weekday()) % 7 or 7)


def modify_sessions(
    sessions: list[dict],
    instruction: str,
    subjects: list[dict],
    exam_date: date,
    daily_hours: float,
    today: date | None = None,
) -> list[dict]:
    updated = deepcopy(sessions)
    text = instruction.lower()
    today = today or date.today()
    forbidden = next(
        (
            number
            for name, number in DAYS.items()
            if (
                f"no {name}" in text
                or f"cannot study on {name}" in text
                or f"can't study on {name}" in text
            )
        ),
        None,
    )
    target_day = next(
        (number for name, number in DAYS.items() if f"to {name}" in text or f"on {name}" in text),
        None,
    )
    subject = next((item["name"] for item in subjects if item["name"].lower() in text), None)

    displaced: list[dict] = []
    if forbidden is not None:
        displaced = [item for item in updated if item["session_date"].weekday() == forbidden]
        updated = [item for item in updated if item["session_date"].weekday() != forbidden]
    elif target_day is not None and subject:
        affected = [item for item in updated if item["subject"] == subject]
        if not affected:
            raise PlanValidationError([f"No sessions found for {subject}"])
        destination = next_weekday(today - timedelta(days=1), target_day)
        for item in affected:
            item["session_date"] = destination
    else:
        hours = re.search(r"(?:only have|limit.*to)\s+(\d+(?:\.\d+)?)\s*hour", text)
        if hours and "tomorrow" in text:
            day = today + timedelta(days=1)
            limit = int(float(hours.group(1)) * 60)
            day_sessions = [item for item in updated if item["session_date"] == day]
            while sum(item["duration_minutes"] for item in day_sessions) > limit and day_sessions:
                moved = day_sessions.pop()
                updated.remove(moved)
                displaced.append(moved)
        else:
            raise PlanValidationError(
                [
                    "I can modify unavailable weekdays, move a named subject, or limit tomorrow's hours"
                ]
            )

    # Preserve unaffected entries and move displaced work to the first day with capacity.
    for item in displaced:
        placed = False
        for offset in range(1, max(1, (exam_date - today).days)):
            candidate = today + timedelta(days=offset)
            if candidate >= exam_date or (
                forbidden is not None and candidate.weekday() == forbidden
            ):
                continue
            used = sum(
                entry["duration_minutes"] for entry in updated if entry["session_date"] == candidate
            )
            if used + item["duration_minutes"] <= daily_hours * 60:
                item["session_date"] = candidate
                updated.append(item)
                placed = True
                break
        if not placed:
            raise PlanValidationError(["The displaced workload cannot fit before the exam"])
    errors = validate_sessions(updated, subjects, exam_date, daily_hours)
    if errors:
        raise PlanValidationError(errors)
    return sorted(updated, key=lambda item: (item["session_date"], item["subject"]))
