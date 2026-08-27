from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Category, Service, ServicePackage
from app.repositories import category_repository, service_repository


def list_categories(db: Session) -> list[Category]:
    return category_repository.get_active_categories(db)


def get_category_or_none(db: Session, category_id: int) -> Category | None:
    cat = category_repository.get_category(db, category_id)
    if cat is None or not cat.is_active:
        return None
    return cat


def list_services(db: Session, category_id: int) -> list[Service]:
    return service_repository.get_active_services_for_category(db, category_id)


def get_service_or_none(db: Session, service_id: int) -> Service | None:
    svc = service_repository.get_service(db, service_id)
    if svc is None or not svc.is_active:
        return None
    return svc


def list_packages(db: Session, service_id: int) -> list[ServicePackage]:
    return service_repository.get_active_packages_for_service(db, service_id)


def get_package_or_none(db: Session, package_id: int) -> ServicePackage | None:
    pkg = service_repository.get_package(db, package_id)
    if pkg is None or not pkg.is_active:
        return None
    return pkg
