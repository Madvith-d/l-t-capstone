import re
from typing import Annotated

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.models import User

USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,36}$")


def get_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> str:
    if not x_user_id or not USER_ID_PATTERN.fullmatch(x_user_id):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "identity_required",
                "message": "A valid 8–36 character X-User-ID session identity is required.",
            },
        )
    return x_user_id


def ensure_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id, display_name="Student")
        db.add(user)
        db.flush()
    return user
