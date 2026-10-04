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


def test_move_subject_defaults_to_one_session_not_all():
    payload = request()
    sessions = generate_sessions(payload)
    original_dbms_dates = [item["session_date"] for item in sessions if item["subject"] == "DBMS"]
    updated = modify_sessions(
        sessions,
        "Move DBMS revision to Monday",
        [item.model_dump() for item in payload.subjects],
        payload.exam_date,
        payload.available_hours_per_day,
    )
    updated_dbms_dates = [item["session_date"] for item in updated if item["subject"] == "DBMS"]
    assert sum(before != after for before, after in zip(sorted(original_dbms_dates), sorted(updated_dbms_dates))) <= 2
    assert len(set(updated_dbms_dates)) > 1


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
