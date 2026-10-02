from collections import defaultdict
from datetime import date, timedelta

from app.schemas.api import PlanCreate


class PlanValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def generate_sessions(request: PlanCreate, today: date | None = None) -> list[dict]:
    start = request.start_date or today or date.today()
    if request.exam_date <= start:
        raise PlanValidationError(["Exam date must be after the plan start date"])
    days = [start + timedelta(days=index) for index in range((request.exam_date - start).days)]
    work = []
    for subject in request.subjects:
        for topic in subject.topics:
            # Harder topics receive more sessions without relying on an LLM.
            for revision in range(max(1, (subject.difficulty + 1) // 2)):
                work.append((subject.name, topic, subject.difficulty, revision))
    work.sort(key=lambda item: (-item[2], item[0], item[1], item[3]))
    daily_limit = int(request.available_hours_per_day * 60)
    allocations: dict[date, int] = defaultdict(int)
    sessions: list[dict] = []
    cursor = 0
    for subject, topic, difficulty, _ in work:
        duration = min(90, max(30, 30 + difficulty * 10))
        placed = False
        for _ in range(len(days)):
            day = days[cursor % len(days)]
            cursor += 1
            if allocations[day] + duration <= daily_limit:
                sessions.append(
                    {
                        "session_date": day,
                        "subject": subject,
                        "topic": topic,
                        "duration_minutes": duration,
                        "preferred_time": request.preferred_times[0]
                        if request.preferred_times
                        else None,
                        "status": "planned",
                    }
                )
                allocations[day] += duration
                placed = True
                break
        if not placed:
            raise PlanValidationError(
                ["Available time is insufficient to cover every requested topic"]
            )
    return sorted(sessions, key=lambda item: (item["session_date"], item["subject"], item["topic"]))


def validate_sessions(
    sessions: list[dict], subjects: list[dict], exam_date: date, available_hours_per_day: float
) -> list[str]:
    errors: list[str] = []
    totals: dict[date, int] = defaultdict(int)
    covered = set()
    for session in sessions:
        session_date = session["session_date"]
        duration = session["duration_minutes"]
        if duration <= 0:
            errors.append(f"{session['subject']} has a non-positive session duration")
        if session_date >= exam_date:
            errors.append(f"{session['subject']} has a session on or after the exam date")
        totals[session_date] += duration
        covered.add(session["subject"])
    for day, total in totals.items():
        if total > available_hours_per_day * 60:
            errors.append(f"{day.isoformat()} exceeds the daily time limit")
    required = {item["name"] if isinstance(item, dict) else item.name for item in subjects}
    for missing in sorted(required - covered):
        errors.append(f"Missing required subject: {missing}")
    return errors
