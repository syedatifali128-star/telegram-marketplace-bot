from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PostingLog, PostingStatus


def start_attempt(db: Session, campaign_id: int, group_id: int, scheduled_for: datetime) -> PostingLog:
    """
    Written BEFORE the Telegram call is made — status SENDING. If the
    process crashes right after this commit but before the result is
    recorded, this row is what lets a restart detect "this attempt's
    outcome is unknown" instead of guessing.
    """
    log = PostingLog(
        campaign_id=campaign_id,
        group_id=group_id,
        scheduled_for=scheduled_for,
        attempted_at=datetime.now(timezone.utc),
        status=PostingStatus.SENDING,
    )
    db.add(log)
    db.flush()
    return log


def mark_success(db: Session, log: PostingLog, telegram_message_id: int | None) -> PostingLog:
    log.status = PostingStatus.SUCCESS
    log.telegram_message_id = telegram_message_id
    db.flush()
    return log


def mark_failed(db: Session, log: PostingLog, error_message: str) -> PostingLog:
    log.status = PostingStatus.FAILED
    log.error_message = error_message[:2000]
    db.flush()
    return log


def mark_skipped(db: Session, campaign_id: int, group_id: int | None, scheduled_for: datetime, reason: str) -> PostingLog:
    log = PostingLog(
        campaign_id=campaign_id,
        group_id=group_id,
        scheduled_for=scheduled_for,
        attempted_at=datetime.now(timezone.utc),
        status=PostingStatus.SKIPPED,
        error_message=reason[:2000],
    )
    db.add(log)
    db.flush()
    return log


def find_stuck_sending(db: Session, older_than_minutes: int = 10) -> list[PostingLog]:
    """Rows left in SENDING past a sane timeout — almost certainly an interrupted run."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    stmt = select(PostingLog).where(PostingLog.status == PostingStatus.SENDING, PostingLog.attempted_at < cutoff)
    return list(db.execute(stmt).scalars().all())


def get_recent_logs(db: Session, limit: int = 50, campaign_id: int | None = None,
                     category_id: int | None = None, group_id: int | None = None,
                     status: PostingStatus | None = None) -> list[PostingLog]:
    stmt = select(PostingLog).order_by(PostingLog.id.desc())
    if campaign_id is not None:
        stmt = stmt.where(PostingLog.campaign_id == campaign_id)
    if group_id is not None:
        stmt = stmt.where(PostingLog.group_id == group_id)
    if status is not None:
        stmt = stmt.where(PostingLog.status == status)
    stmt = stmt.limit(limit)
    logs = list(db.execute(stmt).scalars().all())
    if category_id is not None:
        logs = [l for l in logs if l.campaign.category_id == category_id]
    return logs
