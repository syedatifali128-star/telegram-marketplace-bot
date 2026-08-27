from __future__ import annotations

from app.models import Category, Service, ServicePackage


def test_category_creation(db):
    cat = Category(name="Instagram", icon="📸")
    db.add(cat)
    db.commit()
    assert cat.id is not None
    assert cat.is_active is True  # default


def test_service_and_package_creation(db):
    cat = Category(name="Instagram")
    db.add(cat)
    db.commit()

    svc = Service(category_id=cat.id, name="Followers")
    db.add(svc)
    db.commit()

    pkg = ServicePackage(service_id=svc.id, label="1K", quantity=1000, price=2.0, currency="USD")
    db.add(pkg)
    db.commit()

    assert svc.category_id == cat.id
    assert pkg.service_id == svc.id
    assert pkg.price == 2.0
