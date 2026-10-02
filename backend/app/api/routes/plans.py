from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import StudyPlan, StudySession
from app.planner.engine import PlanValidationError, generate_sessions, validate_sessions
from app.planner.modification import modify_sessions
from app.schemas.api import PlanCreate, PlanOut, PlanPatch

router = APIRouter(prefix="/api/plans", tags=["plans"])


def load_plan(db: Session, plan_id: str) -> StudyPlan:
    plan = db.scalar(
        select(StudyPlan).where(StudyPlan.id == plan_id).options(selectinload(StudyPlan.sessions))
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return plan


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    try:
        generated = generate_sessions(payload)
        errors = validate_sessions(
            generated,
            [item.model_dump() for item in payload.subjects],
            payload.exam_date,
            payload.available_hours_per_day,
        )
        if errors:
            raise PlanValidationError(errors)
    except PlanValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "Study plan is invalid", "errors": exc.errors}
        ) from exc
    plan = StudyPlan(
        user_id=payload.user_id,
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
    db.commit()
    return load_plan(db, plan.id)


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    return load_plan(db, plan_id)


@router.patch("/{plan_id}", response_model=PlanOut)
def patch_plan(plan_id: str, payload: PlanPatch, db: Session = Depends(get_db)):
    plan = load_plan(db, plan_id)
    existing = [
        {
            "session_date": item.session_date,
            "subject": item.subject,
            "topic": item.topic,
            "duration_minutes": item.duration_minutes,
            "preferred_time": item.preferred_time,
            "status": item.status,
        }
        for item in plan.sessions
    ]
    try:
        updated = modify_sessions(
            existing,
            payload.instruction,
            plan.subjects,
            plan.exam_date,
            plan.available_hours_per_day,
        )
    except PlanValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "Plan modification is invalid", "errors": exc.errors},
        ) from exc
    db.execute(delete(StudySession).where(StudySession.plan_id == plan.id))
    for item in updated:
        db.add(StudySession(plan_id=plan.id, **item))
    plan.version += 1
    plan.constraints = {**plan.constraints, "last_instruction": payload.instruction}
    db.commit()
    return load_plan(db, plan.id)
