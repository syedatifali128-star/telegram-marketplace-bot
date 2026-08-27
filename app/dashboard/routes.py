from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database.connection import get_db
from app.models import CampaignStatus, OrderStatus, PaymentVerificationStatus, PostingStatus
from app.repositories import (
    campaign_repository,
    category_repository,
    group_repository,
    order_repository,
    posting_log_repository,
)
from app.services import campaign_service, group_service

router = APIRouter()
templates = Jinja2Templates(directory="app/dashboard/templates")


# ---------------- Dashboard overview ----------------

@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    campaigns = campaign_repository.get_all_campaigns(db)
    groups = group_repository.get_all_groups(db)
    logs = posting_log_repository.get_recent_logs(db, limit=15)

    active_campaigns = [c for c in campaigns if c.status == CampaignStatus.ACTIVE]
    paused_campaigns = [c for c in campaigns if c.status == CampaignStatus.PAUSED]
    active_groups = [g for g in groups if g.is_active]
    success_count = sum(1 for l in logs if l.status == PostingStatus.SUCCESS)
    failed_count = sum(1 for l in logs if l.status == PostingStatus.FAILED)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "admin": admin,
            "active_campaigns": active_campaigns,
            "paused_campaigns": paused_campaigns,
            "active_groups": active_groups,
            "total_categories": len(category_repository.get_all_categories(db)),
            "success_count": success_count,
            "failed_count": failed_count,
            "logs": logs,
        },
    )


# ---------------- Categories ----------------

@router.get("/categories", response_class=HTMLResponse)
def categories_list(request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    categories = category_repository.get_all_categories(db)
    return templates.TemplateResponse("categories.html", {"request": request, "admin": admin, "categories": categories})


@router.post("/categories/create")
def category_create(
    name: str = Form(...), description: str = Form(""), icon: str = Form(""),
    admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    from app.models import Category
    db.add(Category(name=name.strip(), description=description.strip() or None, icon=icon.strip() or None))
    db.commit()
    return RedirectResponse(url="/categories", status_code=303)


@router.post("/categories/{category_id}/toggle")
def category_toggle(category_id: int, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    cat = category_repository.get_category(db, category_id)
    if cat:
        cat.is_active = not cat.is_active
        db.commit()
    return RedirectResponse(url="/categories", status_code=303)


# ---------------- Groups ----------------

@router.get("/groups", response_class=HTMLResponse)
def groups_list(request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    groups = group_service.list_groups(db)
    categories = category_repository.get_active_categories(db)
    return templates.TemplateResponse(
        "groups.html", {"request": request, "admin": admin, "groups": groups, "categories": categories}
    )


@router.post("/groups/create")
def group_create(
    telegram_chat_id: int = Form(...), name: str = Form(...), username_or_link: str = Form(""),
    category_ids: list[int] = Form(default=[]),
    admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    try:
        group_service.add_group(db, telegram_chat_id, name, username_or_link.strip() or None, category_ids)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return RedirectResponse(url="/groups", status_code=303)


@router.post("/groups/{group_id}/toggle")
def group_toggle(group_id: int, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    group = group_repository.get_group(db, group_id)
    if group:
        if group.is_active:
            group_service.deactivate_group(db, group)
        else:
            group_service.activate_group(db, group)
        db.commit()
    return RedirectResponse(url="/groups", status_code=303)


# ---------------- Campaigns ----------------

@router.get("/campaigns", response_class=HTMLResponse)
def campaigns_list(request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    campaigns = campaign_repository.get_all_campaigns(db)
    categories = category_repository.get_active_categories(db)
    return templates.TemplateResponse(
        "campaigns.html", {"request": request, "admin": admin, "campaigns": campaigns, "categories": categories}
    )


@router.post("/campaigns/create")
def campaign_create(
    name: str = Form(...), category_id: int = Form(...), message_text: str = Form(...),
    interval_seconds: int = Form(...), timezone: str = Form("Asia/Kolkata"),
    admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    error = None
    try:
        campaign_service.create_campaign(db, name, category_id, message_text, interval_seconds, timezone)
        db.commit()
    except campaign_service.CampaignValidationError as e:
        db.rollback()
        error = str(e)
    if error:
        return RedirectResponse(url=f"/campaigns?error={error}", status_code=303)
    return RedirectResponse(url="/campaigns", status_code=303)


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse)
def campaign_detail(
    campaign_id: int, request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)
):
    campaign = campaign_repository.get_campaign(db, campaign_id)
    all_groups = group_repository.get_active_groups(db)
    assigned = {g.id for g in campaign_repository.get_assigned_groups(db, campaign_id)}
    logs = posting_log_repository.get_recent_logs(db, limit=30, campaign_id=campaign_id)
    return templates.TemplateResponse(
        "campaign_detail.html",
        {
            "request": request, "admin": admin, "campaign": campaign, "all_groups": all_groups,
            "assigned_ids": assigned, "logs": logs,
        },
    )


@router.post("/campaigns/{campaign_id}/assign-groups")
def campaign_assign_groups(
    campaign_id: int, group_ids: list[int] = Form(default=[]),
    admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    campaign = campaign_repository.get_campaign(db, campaign_id)
    if campaign:
        campaign_service.assign_groups(db, campaign, group_ids)
        db.commit()
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)


@router.post("/campaigns/{campaign_id}/pause")
def campaign_pause(campaign_id: int, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = campaign_repository.get_campaign(db, campaign_id)
    if campaign:
        campaign_service.pause_campaign(db, campaign)
        db.commit()
    return RedirectResponse(url=f"/campaigns/{campaign_id}", status_code=303)


@router.post("/campaigns/{campaign_id}/resume")
def campaign_resume(campaign_id: int, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = campaign_repository.get_campaign(db, campaign_id)
    error = None
    if campaign:
        try:
            campaign_service.resume_campaign(db, campaign)
            db.commit()
        except campaign_service.CampaignValidationError as e:
            db.rollback()
            error = str(e)
    url = f"/campaigns/{campaign_id}" + (f"?error={error}" if error else "")
    return RedirectResponse(url=url, status_code=303)


@router.post("/campaigns/{campaign_id}/edit-message")
def campaign_edit_message(
    campaign_id: int, message_text: str = Form(...),
    admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    campaign = campaign_repository.get_campaign(db, campaign_id)
    error = None
    if campaign:
        try:
            campaign_service.update_message(db, campaign, message_text, campaign.media_file_id)
            db.commit()
        except campaign_service.CampaignValidationError as e:
            db.rollback()
            error = str(e)
    url = f"/campaigns/{campaign_id}" + (f"?error={error}" if error else "")
    return RedirectResponse(url=url, status_code=303)


# ---------------- Logs ----------------

@router.get("/logs", response_class=HTMLResponse)
def logs_view(
    request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db),
    campaign_id: int | None = None, status: str | None = None,
):
    status_enum = PostingStatus(status) if status else None
    logs = posting_log_repository.get_recent_logs(db, limit=100, campaign_id=campaign_id, status=status_enum)
    campaigns = campaign_repository.get_all_campaigns(db)
    return templates.TemplateResponse(
        "logs.html",
        {"request": request, "admin": admin, "logs": logs, "campaigns": campaigns, "statuses": list(PostingStatus)},
    )


# ---------------- Services (customer-facing catalog admin) ----------------

@router.get("/services", response_class=HTMLResponse)
def services_list(request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    from app.models import Service
    services = db.query(Service).order_by(Service.id).all()
    categories = category_repository.get_active_categories(db)
    return templates.TemplateResponse(
        "services.html", {"request": request, "admin": admin, "services": services, "categories": categories}
    )


@router.post("/services/create")
def service_create(
    category_id: int = Form(...), name: str = Form(...), description: str = Form(""),
    admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    from app.models import Service
    db.add(Service(category_id=category_id, name=name.strip(), description=description.strip() or None))
    db.commit()
    return RedirectResponse(url="/services", status_code=303)


@router.post("/services/{service_id}/packages/create")
def package_create(
    service_id: int, label: str = Form(...), quantity: int = Form(...), price: float = Form(...),
    currency: str = Form("USD"), admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    from app.models import ServicePackage
    db.add(ServicePackage(service_id=service_id, label=label.strip(), quantity=quantity, price=price, currency=currency))
    db.commit()
    return RedirectResponse(url="/services", status_code=303)


@router.post("/packages/{package_id}/edit")
def package_edit(
    package_id: int, label: str = Form(...), quantity: int = Form(...), price: float = Form(...),
    currency: str = Form("USD"), admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    """
    Updates an EXISTING package's price/label/quantity in place — this is
    how a client updates the price shown to customers in the bot (e.g.
    "1K Followers" going from $2 to $3) without creating a duplicate
    package. Takes effect immediately for new orders; doesn't touch
    orders already placed at the old price.
    """
    from app.repositories import service_repository
    package = service_repository.get_package(db, package_id)
    if package:
        service_repository.update_package(db, package, label.strip(), quantity, price, currency)
        db.commit()
    return RedirectResponse(url="/services", status_code=303)


@router.post("/packages/{package_id}/toggle")
def package_toggle(package_id: int, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    from app.repositories import service_repository
    package = service_repository.get_package(db, package_id)
    if package:
        service_repository.set_package_active(db, package, is_active=not package.is_active)
        db.commit()
    return RedirectResponse(url="/services", status_code=303)


# ---------------- Orders / payment verification ----------------

@router.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)):
    from app.models import Order
    orders = db.query(Order).order_by(Order.id.desc()).limit(100).all()
    return templates.TemplateResponse("orders.html", {"request": request, "admin": admin, "orders": orders})


@router.post("/orders/{order_id}/verify-payment")
def verify_payment(
    order_id: int, decision: str = Form(...),
    admin: str = Depends(require_admin), db: Session = Depends(get_db),
):
    """
    Explicit, manual admin action. This is the ONLY way a payment moves out
    of PENDING_VERIFICATION — see payment model docstring.
    """
    order = order_repository.get_order(db, order_id)
    if order and order.payment:
        if decision == "approve":
            order.payment.verification_status = PaymentVerificationStatus.VERIFIED
            order.status = OrderStatus.PAID
        elif decision == "reject":
            order.payment.verification_status = PaymentVerificationStatus.REJECTED
            order.status = OrderStatus.CANCELLED
        order.payment.verified_by = admin
        from datetime import datetime, timezone
        order.payment.verified_at = datetime.now(timezone.utc)
        db.commit()
    return RedirectResponse(url="/orders", status_code=303)
