from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_or_create_user(
    db: Session, telegram_user_id: int, username: str | None, first_name: str | None
) -> User:
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    user = db.execute(stmt).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_activity_at=now,
        )
        db.add(user)
        db.flush()
    else:
        user.username = username
        user.first_name = first_name
        user.last_activity_at = now
    return user


def get_user_by_telegram_id(db: Session, telegram_user_id: int) -> User | None:
    stmt = select(User).where(User.telegram_user_id == telegram_user_id)
    return db.execute(stmt).scalar_one_or_none()
