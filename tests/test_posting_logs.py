from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Category, Group, PostingStatus
from app.repositories import campaign_repository, posting_log_repository


def _setup(db):
    cat = Category(name="SMM")
    db.add(cat)
    db.commit()
    campaign = campaign_repository.create_campaign(
        db, name="X", category_id=cat.id, message_text="hi", interval_seconds=600, timezone="UTC"
    )
    group = Group(telegram_chat_id=555, name="G1")
    db.add(group)
    db.commit()
    return campaign, group


def test_posting_log_success_lifecycle(db):
    campaign, group = _setup(db)
    now = datetime.now(timezone.utc)
    log = posting_log_repository.start_attempt(db, campaign.id, group.id, scheduled_for=now)
    assert log.status == PostingStatus.SENDING

    posting_log_repository.mark_success(db, log, telegram_message_id=999)
    assert log.status == PostingStatus.SUCCESS
    assert log.telegram_message_id == 999


def test_posting_log_failure_lifecycle(db):
    campaign, group = _setup(db)
    now = datetime.now(timezone.utc)
    log = posting_log_repository.start_attempt(db, campaign.id, group.id, scheduled_for=now)
    posting_log_repository.mark_failed(db, log, "Forbidden: bot was kicked")
    assert log.status == PostingStatus.FAILED
    assert "kicked" in log.error_message


def test_stuck_sending_detection_and_recovery(db):
    """
    Simulates the crash scenario from spec section 9: a row left in
    SENDING past the timeout is treated as unknown-outcome and flagged,
    never silently resent.
    """
    campaign, group = _setup(db)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    log = posting_log_repository.start_attempt(db, campaign.id, group.id, scheduled_for=old_time)
    log.attempted_at = old_time  # simulate an attempt from 30 minutes ago
    db.commit()

    stuck = posting_log_repository.find_stuck_sending(db, older_than_minutes=10)
    assert len(stuck) == 1
    assert stuck[0].id == log.id

    posting_log_repository.mark_failed(db, stuck[0], "Interrupted before result was recorded — verify manually.")
    assert log.status == PostingStatus.FAILED

    # After recovery, it should no longer show up as stuck.
    assert posting_log_repository.find_stuck_sending(db, older_than_minutes=10) == []


def test_fresh_sending_row_not_flagged_as_stuck(db):
    campaign, group = _setup(db)
    posting_log_repository.start_attempt(db, campaign.id, group.id, scheduled_for=datetime.now(timezone.utc))
    stuck = posting_log_repository.find_stuck_sending(db, older_than_minutes=10)
    assert stuck == []  # too recent to be considered stuck
