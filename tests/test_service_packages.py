from __future__ import annotations

from app.models import Category, Service, ServicePackage
from app.repositories import service_repository


def test_package_price_update(db):
    cat = Category(name="Instagram")
    db.add(cat)
    db.commit()
    svc = Service(category_id=cat.id, name="Followers")
    db.add(svc)
    db.commit()
    pkg = ServicePackage(service_id=svc.id, label="1K", quantity=1000, price=2.0, currency="USD")
    db.add(pkg)
    db.commit()

    service_repository.update_package(db, pkg, label="1K", quantity=1000, price=3.5, currency="USD")
    db.commit()

    assert pkg.price == 3.5


def test_package_deactivate_reactivate(db):
    cat = Category(name="Instagram")
    db.add(cat)
    db.commit()
    svc = Service(category_id=cat.id, name="Followers")
    db.add(svc)
    db.commit()
    pkg = ServicePackage(service_id=svc.id, label="1K", quantity=1000, price=2.0, currency="USD")
    db.add(pkg)
    db.commit()

    service_repository.set_package_active(db, pkg, is_active=False)
    db.commit()
    assert pkg.is_active is False

    # deactivated packages must not show up in the customer-facing list
    from app.services import catalog_service
    assert pkg not in catalog_service.list_packages(db, svc.id)

    service_repository.set_package_active(db, pkg, is_active=True)
    db.commit()
    assert pkg in catalog_service.list_packages(db, svc.id)
