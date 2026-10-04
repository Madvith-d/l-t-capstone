from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.api import DemoStatus
from app.services.demo import DEMO_NOTICE, DEMO_QUESTIONS

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("", response_model=DemoStatus)
def demo_status() -> DemoStatus:
    enabled = get_settings().demo_mode
    return DemoStatus(
        enabled=enabled,
        label=DEMO_NOTICE if enabled else "Live knowledge-base mode",
        questions=DEMO_QUESTIONS if enabled else [],
    )
