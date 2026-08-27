from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Service, ServicePackage


def get_active_services_for_category(db: Session, category_id: int) -> list[Service]:
    stmt = (
        select(Service)
        .where(Service.category_id == category_id, Service.is_active.is_(True))
        .order_by(Service.id)
    )
    return list(db.execute(stmt).scalars().all())


def get_service(db: Session, service_id: int) -> Service | None:
    return db.get(Service, service_id)


def get_active_packages_for_service(db: Session, service_id: int) -> list[ServicePackage]:
    stmt = (
        select(ServicePackage)
        .where(ServicePackage.service_id == service_id, ServicePackage.is_active.is_(True))
        .order_by(ServicePackage.price)
    )
    return list(db.execute(stmt).scalars().all())


def get_package(db: Session, package_id: int) -> ServicePackage | None:
    return db.get(ServicePackage, package_id)


def update_package(
    db: Session, package: ServicePackage, label: str, quantity: int, price: float, currency: str
) -> ServicePackage:
    package.label = label
    package.quantity = quantity
    package.price = price
    package.currency = currency
    db.flush()
    return package


def set_package_active(db: Session, package: ServicePackage, is_active: bool) -> ServicePackage:
    package.is_active = is_active
    db.flush()
    return package
