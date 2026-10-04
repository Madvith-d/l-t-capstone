import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import ensure_user
from app.models import StudyPlan, StudySession
from app.planner.engine import PlanValidationError, generate_sessions, validate_sessions
from app.planner.modification import ModificationCommand, apply_modification, parse_modification
from app.schemas.api import PlanCreate, SubjectInput


def load_plan(db: Session, user_id: str, plan_id: str) -> StudyPlan | None:
    return db.scalar(
        select(StudyPlan)
        .where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
        .options(selectinload(StudyPlan.sessions))
    )


def latest_plan(db: Session, user_id: str) -> StudyPlan | None:
    return db.scalar(
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id)
        .options(selectinload(StudyPlan.sessions))
        .order_by(StudyPlan.updated_at.desc())
        .limit(1)
    )


def list_plans(db: Session, user_id: str) -> list[StudyPlan]:
    return list(
        db.scalars(
            select(StudyPlan)
            .where(StudyPlan.user_id == user_id)
            .options(selectinload(StudyPlan.sessions))
            .order_by(StudyPlan.updated_at.desc())
            .limit(50)
        ).all()
    )


def create_plan(db: Session, user_id: str, payload: PlanCreate) -> StudyPlan:
    ensure_user(db, user_id)
    generated = generate_sessions(payload)
    errors = validate_sessions(
        generated,
        [item.model_dump() for item in payload.subjects],
        payload.exam_date,
        payload.available_hours_per_day,
    )
    if errors:
        raise PlanValidationError(errors)
    plan = StudyPlan(
        user_id=user_id,
        title=payload.title,
        exam_date=payload.exam_date,
        available_hours_per_day=payload.available_hours_per_day,
        subjects=[item.model_dump() for item in payload.subjects],
        constraints={"preferred_times": payload.preferred_times},
    )
    db.add(plan)
    db.flush()
    for item in generated:
        db.add(StudySession(plan_id=plan.id, **item))
    db.flush()
    return load_plan(db, user_id, plan.id) or plan


def session_dicts(plan: StudyPlan) -> list[dict]:
    return [
        {
            "id": item.id,
            "session_date": item.session_date,
            "subject": item.subject,
            "topic": item.topic,
            "duration_minutes": item.duration_minutes,
            "preferred_time": item.preferred_time,
            "status": item.status,
        }
        for item in plan.sessions
    ]


def sync_sessions(db: Session, plan: StudyPlan, updated: list[dict]) -> None:
    existing = {item.id: item for item in plan.sessions}
    retained: set[str] = set()
    for data in updated:
        session_id = data.get("id")
        row = existing.get(session_id) if session_id else None
        if row is None:
            row = StudySession(plan_id=plan.id)
            db.add(row)
        else:
            retained.add(row.id)
        for field in (
            "session_date",
            "subject",
            "topic",
            "duration_minutes",
            "preferred_time",
            "status",
        ):
            setattr(row, field, data[field])
    for session_id, row in existing.items():
        if session_id not in retained:
            db.delete(row)


def modify_plan(
    db: Session,
    user_id: str,
    plan: StudyPlan,
    instruction: str,
    command: ModificationCommand | None = None,
) -> StudyPlan:
    command = command or parse_modification(instruction, plan.subjects)
    updated = apply_modification(
        session_dicts(plan),
        command,
        plan.subjects,
        plan.exam_date,
        plan.available_hours_per_day,
    )
    sync_sessions(db, plan, updated)
    plan.version += 1
    plan.constraints = {
        **plan.constraints,
        "last_instruction": instruction,
        "last_command": command.model_dump(mode="json"),
    }
    db.flush()
    db.expire(plan, ["sessions"])
    return load_plan(db, user_id, plan.id) or plan


def parse_chat_plan_request(question: str, user_id: str) -> PlanCreate:
    text = question.strip()
    duration_match = re.search(r"\b(\d{1,3})[- ]day\b", text, re.IGNORECASE)
    hours_match = re.search(r"\b(\d+(?:\.\d+)?)\s*hours?\s*(?:/|per)\s*day\b", text, re.IGNORECASE)
    date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    subject_match = re.search(
        r"\bfor\s+(.+?)(?:\.|,|\s+with\s+|\s+until\s+|\s+i\s+have\b|$)",
        text,
        re.IGNORECASE,
    )
    if not subject_match:
        raise PlanValidationError(
            ["Include subjects, for example: Create a 14-day plan for DBMS and OS, 3 hours per day."]
        )
    names = [
        value.strip(" .")
        for value in re.split(r"\s+and\s+|,", subject_match.group(1), flags=re.IGNORECASE)
        if value.strip(" .")
    ]
    if not names:
        raise PlanValidationError(["At least one subject is required"])
    start = date.today()
    exam_date = (
        date.fromisoformat(date_match.group(1))
        if date_match
        else start + timedelta(days=int(duration_match.group(1)) if duration_match else 14)
    )
    hours = float(hours_match.group(1)) if hours_match else 3.0
    return PlanCreate(
        user_id=user_id,
        subjects=[SubjectInput(name=name, topics=["General review"], difficulty=3) for name in names],
        exam_date=exam_date,
        available_hours_per_day=hours,
        start_date=start,
    )
