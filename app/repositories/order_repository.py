from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, Payment, PaymentVerificationStatus, ServicePackage


def create_order(db: Session, user_id: int, package: ServicePackage, target: str) -> Order:
    order = Order(
        user_id=user_id,
        service_package_id=package.id,
        quantity=package.quantity,
        target=target,
        amount=package.price,
        currency=package.currency,
        status=OrderStatus.PENDING_PAYMENT,
    )
    db.add(order)
    db.flush()
    return order


def get_order(db: Session, order_id: int) -> Order | None:
    return db.get(Order, order_id)


def get_orders_for_user(db: Session, user_id: int) -> list[Order]:
    stmt = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def submit_payment_reference(
    db: Session, order: Order, amount: float, method: str | None, reference: str
) -> Payment:
    """
    Record a customer's payment reference. Always PENDING_VERIFICATION —
    never auto-marked paid, per spec section 3. Admin verification (a
    separate, explicit action) is what moves this forward.
    """
    payment = Payment(
        order_id=order.id,
        amount=amount,
        method=method,
        reference=reference,
        verification_status=PaymentVerificationStatus.PENDING_VERIFICATION,
    )
    db.add(payment)
    order.status = OrderStatus.PAYMENT_SUBMITTED
    db.flush()
    return payment
