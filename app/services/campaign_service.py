from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Campaign, CampaignStatus, Group, GroupCategory
from app.repositories import campaign_repository, category_repository, group_repository

# Floor on posting interval — a deliberate anti-spam safeguard, not a
# workaround. Keeps V1 from being usable to hammer groups too aggressively.
MIN_INTERVAL_SECONDS = 300  # 5 minutes

ALLOWED_TEMPLATE_VARS = {"campaign_name", "category", "date", "time"}
_TEMPLATE_VAR_RE = re.compile(r"\{([a-zA-Z_]+)\}")


class CampaignValidationError(ValueError):
    pass


def validate_template(message_text: str) -> None:
    if not message_text.strip():
        raise CampaignValidationError("Message text is required.")
    used_vars = set(_TEMPLATE_VAR_RE.findall(message_text))
    unknown = used_vars - ALLOWED_TEMPLATE_VARS
    if unknown:
        raise CampaignValidationError(
            f"Unknown template variable(s): {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_TEMPLATE_VARS))}"
        )


def render_message(campaign: Campaign, category_name: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    return campaign.message_text.format(
        campaign_name=campaign.name,
        category=category_name,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
    )


def create_campaign(
    db: Session,
    name: str,
    category_id: int,
    message_text: str,
    interval_seconds: int,
    timezone: str = "Asia/Kolkata",
    media_file_id: str | None = None,
) -> Campaign:
    if not name.strip():
        raise CampaignValidationError("Campaign name is required.")
    category = category_repository.get_category(db, category_id)
    if category is None or not category.is_active:
        raise CampaignValidationError("Selected category does not exist or is inactive.")
    if interval_seconds < MIN_INTERVAL_SECONDS:
        raise CampaignValidationError(f"Interval must be at least {MIN_INTERVAL_SECONDS} seconds.")
    validate_template(message_text)

    return campaign_repository.create_campaign(
        db,
        name=name.strip(),
        category_id=category_id,
        message_text=message_text,
        interval_seconds=interval_seconds,
        timezone=timezone,
        media_file_id=media_file_id,
    )


def update_message(db: Session, campaign: Campaign, message_text: str, media_file_id: str | None) -> Campaign:
    validate_template(message_text)
    return campaign_repository.update_message(db, campaign, message_text, media_file_id)


def update_schedule(db: Session, campaign: Campaign, interval_seconds: int, timezone: str) -> Campaign:
    if interval_seconds < MIN_INTERVAL_SECONDS:
        raise CampaignValidationError(f"Interval must be at least {MIN_INTERVAL_SECONDS} seconds.")
    return campaign_repository.update_schedule(db, campaign, interval_seconds, timezone)


def pause_campaign(db: Session, campaign: Campaign) -> Campaign:
    return campaign_repository.set_status(db, campaign, CampaignStatus.PAUSED)


def resume_campaign(db: Session, campaign: Campaign) -> Campaign:
    groups = campaign_repository.get_assigned_groups(db, campaign.id)
    if not groups:
        raise CampaignValidationError("Cannot activate a campaign with no assigned groups.")
    return campaign_repository.set_status(db, campaign, CampaignStatus.ACTIVE)


def assign_groups(db: Session, campaign: Campaign, group_ids: list[int]) -> tuple[Campaign, list[str]]:
    """
    Assign groups to a campaign. This is the ONLY way a campaign gets
    targets (see campaign_repository.get_assigned_groups) — admin choice
    is authoritative, so cross-category assignment is allowed but flagged
    back as a warning rather than silently allowed or silently blocked.
    """
    warnings: list[str] = []
    valid_ids: list[int] = []
    for gid in group_ids:
        group = group_repository.get_group(db, gid)
        if group is None:
            warnings.append(f"Group id {gid} does not exist — skipped.")
            continue
        if not group.is_active:
            warnings.append(f"Group '{group.name}' is inactive — skipped.")
            continue
        group_category_ids = {gc.category_id for gc in group.categories}
        if campaign.category_id not in group_category_ids:
            warnings.append(
                f"Group '{group.name}' is not tagged for this campaign's category — "
                "assigned anyway since you selected it explicitly."
            )
        valid_ids.append(group.id)

    campaign = campaign_repository.assign_groups(db, campaign, valid_ids)
    return campaign, warnings


def get_targets(db: Session, campaign: Campaign) -> list[Group]:
    return campaign_repository.get_assigned_groups(db, campaign.id)
