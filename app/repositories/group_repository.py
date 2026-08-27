from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Group, GroupCategory


def create_group(
    db: Session, telegram_chat_id: int, name: str, username_or_link: str | None, category_ids: list[int]
) -> Group:
    group = Group(telegram_chat_id=telegram_chat_id, name=name, username_or_link=username_or_link)
    db.add(group)
    db.flush()
    for cat_id in category_ids:
        db.add(GroupCategory(group_id=group.id, category_id=cat_id))
    db.flush()
    return group


def get_group(db: Session, group_id: int) -> Group | None:
    return db.get(Group, group_id)


def get_all_groups(db: Session) -> list[Group]:
    return list(db.execute(select(Group).order_by(Group.id)).scalars().all())


def get_active_groups(db: Session) -> list[Group]:
    return list(db.execute(select(Group).where(Group.is_active.is_(True)).order_by(Group.id)).scalars().all())


def set_group_active(db: Session, group: Group, is_active: bool) -> Group:
    group.is_active = is_active
    db.flush()
    return group


def assign_categories(db: Session, group: Group, category_ids: list[int]) -> Group:
    """Replace a group's category assignments with the given set."""
    db.query(GroupCategory).filter(GroupCategory.group_id == group.id).delete()
    for cat_id in category_ids:
        db.add(GroupCategory(group_id=group.id, category_id=cat_id))
    db.flush()
    return group


def record_post_success(db: Session, group: Group, when) -> None:
    group.last_successful_post_at = when
    group.bot_has_permission = True
    db.flush()


def record_post_failure(db: Session, group: Group, when, reason: str) -> None:
    group.last_failure_at = when
    group.last_failure_reason = reason[:500]
    if "not enough rights" in reason.lower() or "permission" in reason.lower():
        group.bot_has_permission = False
    db.flush()
