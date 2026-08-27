from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Campaign, CampaignGroup, CampaignStatus, Group


def create_campaign(
    db: Session,
    name: str,
    category_id: int,
    message_text: str,
    interval_seconds: int,
    timezone: str,
    media_file_id: str | None = None,
) -> Campaign:
    campaign = Campaign(
        name=name,
        category_id=category_id,
        message_text=message_text,
        media_file_id=media_file_id,
        interval_seconds=interval_seconds,
        timezone=timezone,
        status=CampaignStatus.PAUSED,  # created paused; admin explicitly activates
    )
    db.add(campaign)
    db.flush()
    return campaign


def get_campaign(db: Session, campaign_id: int) -> Campaign | None:
    return db.get(Campaign, campaign_id)


def get_all_campaigns(db: Session) -> list[Campaign]:
    return list(db.execute(select(Campaign).order_by(Campaign.id)).scalars().all())


def get_active_campaigns(db: Session) -> list[Campaign]:
    stmt = select(Campaign).where(Campaign.status == CampaignStatus.ACTIVE)
    return list(db.execute(stmt).scalars().all())


def set_status(db: Session, campaign: Campaign, status: CampaignStatus) -> Campaign:
    campaign.status = status
    db.flush()
    return campaign


def update_message(db: Session, campaign: Campaign, message_text: str, media_file_id: str | None) -> Campaign:
    campaign.message_text = message_text
    campaign.media_file_id = media_file_id
    db.flush()
    return campaign


def update_schedule(db: Session, campaign: Campaign, interval_seconds: int, timezone: str) -> Campaign:
    campaign.interval_seconds = interval_seconds
    campaign.timezone = timezone
    db.flush()
    return campaign


def record_execution(db: Session, campaign: Campaign, last_run: datetime, next_run: datetime | None) -> Campaign:
    campaign.last_execution_at = last_run
    campaign.next_execution_at = next_run
    db.flush()
    return campaign


# --- Explicit campaign -> group assignment: the isolation boundary ---

def assign_groups(db: Session, campaign: Campaign, group_ids: list[int]) -> Campaign:
    """
    Replace a campaign's target group assignments with exactly the given
    set. There is no other path by which a campaign acquires targets —
    the scheduler reads ONLY these rows (see get_assigned_groups).
    """
    db.query(CampaignGroup).filter(CampaignGroup.campaign_id == campaign.id).delete()
    for gid in group_ids:
        db.add(CampaignGroup(campaign_id=campaign.id, group_id=gid, is_active=True))
    db.flush()
    return campaign


def get_assigned_groups(db: Session, campaign_id: int) -> list[Group]:
    """
    The single source of truth for "where can this campaign post". Only
    rows in campaign_groups (with is_active=True on both the link and the
    group) are returned — never a category-based lookup.
    """
    stmt = (
        select(Group)
        .join(CampaignGroup, CampaignGroup.group_id == Group.id)
        .where(
            CampaignGroup.campaign_id == campaign_id,
            CampaignGroup.is_active.is_(True),
            Group.is_active.is_(True),
        )
    )
    return list(db.execute(stmt).scalars().all())
