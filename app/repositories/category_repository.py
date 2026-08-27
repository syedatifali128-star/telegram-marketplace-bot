from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category


def get_active_categories(db: Session) -> list[Category]:
    stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.id)
    return list(db.execute(stmt).scalars().all())


def get_category(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_all_categories(db: Session) -> list[Category]:
    """Includes inactive — for the admin dashboard."""
    return list(db.execute(select(Category).order_by(Category.id)).scalars().all())
