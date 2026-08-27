from __future__ import annotations

from app.models import Category, OrderStatus, PaymentVerificationStatus, Service, ServicePackage, User
from app.services import order_service


def _setup_order(db):
    cat = Category(name="Instagram")
    db.add(cat)
    db.commit()
    svc = Service(category_id=cat.id, name="Followers")
    db.add(svc)
    db.commit()
    pkg = ServicePackage(service_id=svc.id, label="1K", quantity=1000, price=2.0, currency="USD")
    db.add(pkg)
    user = User(telegram_user_id=99999, username="tester")
    db.add(user)
    db.commit()
    return user, pkg


def test_order_creation(db):
    user, pkg = _setup_order(db)
    order = order_service.place_order(db, user=user, package=pkg, target="@myprofile")
    db.commit()
    assert order.id is not None
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.amount == pkg.price


def test_payment_submission_never_auto_verifies(db):
    """Critical business rule: submitting a reference must NEVER move payment
    straight to VERIFIED / order straight to PAID — only an explicit admin
    action does that (tested at the dashboard route level, not here)."""
    user, pkg = _setup_order(db)
    order = order_service.place_order(db, user=user, package=pkg, target="@myprofile")
    db.commit()

    payment = order_service.submit_payment(db, order=order, reference="UTR123456")
    db.commit()

    assert payment.verification_status == PaymentVerificationStatus.PENDING_VERIFICATION
    assert order.status == OrderStatus.PAYMENT_SUBMITTED
    assert order.status != OrderStatus.PAID  # explicit negative check on the critical rule


def test_get_my_orders_returns_users_orders_only(db):
    user1, pkg = _setup_order(db)
    user2 = User(telegram_user_id=88888, username="other")
    db.add(user2)
    db.commit()

    order_service.place_order(db, user=user1, package=pkg, target="@a")
    order_service.place_order(db, user=user2, package=pkg, target="@b")
    db.commit()

    user1_orders = order_service.get_my_orders(db, user1)
    assert len(user1_orders) == 1
    assert user1_orders[0].target == "@a"
