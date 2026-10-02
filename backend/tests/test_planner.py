from datetime import date, timedelta

from app.planner.engine import generate_sessions, validate_sessions
from app.planner.modification import modify_sessions
from app.schemas.api import PlanCreate, SubjectInput


def request():
    return PlanCreate(
        subjects=[
            SubjectInput(name="DBMS", topics=["SQL", "Normalization"], difficulty=4),
            SubjectInput(name="OS", topics=["Scheduling"], difficulty=3),
        ],
        exam_date=date.today() + timedelta(days=14),
        available_hours_per_day=3,
    )


def test_generated_plan_is_valid_and_covers_subjects():
    payload = request()
    sessions = generate_sessions(payload)
    assert (
        validate_sessions(
            sessions,
            [item.model_dump() for item in payload.subjects],
            payload.exam_date,
            payload.available_hours_per_day,
        )
        == []
    )
    assert {item["subject"] for item in sessions} == {"DBMS", "OS"}


def test_remove_saturday_preserves_other_sessions():
    payload = request()
    sessions = generate_sessions(payload)
    before = [item.copy() for item in sessions if item["session_date"].weekday() != 5]
    updated = modify_sessions(
        sessions,
        "I cannot study on Saturday",
        [item.model_dump() for item in payload.subjects],
        payload.exam_date,
        payload.available_hours_per_day,
    )
    assert not any(item["session_date"].weekday() == 5 for item in updated)
    for item in before:
        assert item in updated
