from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Order, Payment, ServicePackage, User
from app.repositories import order_repository


def place_order(db: Session, user: User, package: ServicePackage, target: str) -> Order:
    return order_repository.create_order(db, user_id=user.id, package=package, target=target)


def get_my_orders(db: Session, user: User) -> list[Order]:
    return order_repository.get_orders_for_user(db, user.id)


def submit_payment(
    db: Session, order: Order, reference: str, method: str | None = None
) -> Payment:
    """
    Business rule lives here, not in the handler: a submitted reference
    NEVER auto-confirms payment. It only ever creates/updates a
    PENDING_VERIFICATION payment row. See repository docstring for detail.
    """
    return order_repository.submit_payment_reference(
        db, order=order, amount=float(order.amount), method=method, reference=reference
    )
