from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Group
from app.repositories import group_repository


class GroupValidationError(ValueError):
    pass


def add_group(
    db: Session, telegram_chat_id: int, name: str, username_or_link: str | None, category_ids: list[int]
) -> Group:
    if not name.strip():
        raise GroupValidationError("Group name is required.")
    if not category_ids:
        raise GroupValidationError("Assign at least one category to the group.")
    return group_repository.create_group(
        db, telegram_chat_id=telegram_chat_id, name=name.strip(), username_or_link=username_or_link, category_ids=category_ids
    )


def list_groups(db: Session, only_active: bool = False) -> list[Group]:
    return group_repository.get_active_groups(db) if only_active else group_repository.get_all_groups(db)


def deactivate_group(db: Session, group: Group) -> Group:
    return group_repository.set_group_active(db, group, is_active=False)


def activate_group(db: Session, group: Group) -> Group:
    return group_repository.set_group_active(db, group, is_active=True)


def reassign_categories(db: Session, group: Group, category_ids: list[int]) -> Group:
    if not category_ids:
        raise GroupValidationError("A group must have at least one category.")
    return group_repository.assign_categories(db, group, category_ids)
