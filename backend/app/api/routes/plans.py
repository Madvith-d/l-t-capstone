from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_user_id
from app.core.config import get_settings
from app.db.session import get_db
from app.planner.engine import PlanValidationError
from app.schemas.api import PlanCreate, PlanOut, PlanPatch
from app.services.demo import demo_plan_requests, ensure_demo_plans
from app.services.plans import create_plan as create_plan_service
from app.services.plans import list_plans, load_plan, modify_plan

router = APIRouter(prefix="/api/plans", tags=["plans"])


def require_plan(db: Session, user_id: str, plan_id: str):
    plan = load_plan(db, user_id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return plan


@router.get("", response_model=list[PlanOut])
def get_plans(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    if get_settings().demo_mode:
        ensure_demo_plans(db, user_id)
        db.commit()
        demo_titles = {request.title for request in demo_plan_requests()}
        return [plan for plan in list_plans(db, user_id) if plan.title in demo_titles]
    return list_plans(db, user_id)


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(
    payload: PlanCreate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    if payload.user_id and payload.user_id != user_id:
        raise HTTPException(status_code=403, detail="User identity does not match the request")
    try:
        plan = create_plan_service(db, user_id, payload)
        db.commit()
        return require_plan(db, user_id, plan.id)
    except PlanValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_plan", "message": "Study plan is invalid", "errors": exc.errors},
        ) from exc


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: str,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    return require_plan(db, user_id, plan_id)


@router.patch("/{plan_id}", response_model=PlanOut)
def patch_plan(
    plan_id: str,
    payload: PlanPatch,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    plan = require_plan(db, user_id, plan_id)
    try:
        updated = modify_plan(db, user_id, plan, payload.instruction)
        db.commit()
        return require_plan(db, user_id, updated.id)
    except PlanValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_plan_modification",
                "message": "Plan modification is invalid",
                "errors": exc.errors,
            },
        ) from exc
