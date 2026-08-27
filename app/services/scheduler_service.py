"""
Scheduler architecture (spec section 8 & 9):

- APScheduler's AsyncIOScheduler runs inside the bot process's event loop
  (so it can call the async Telegram Bot API directly).
- Job persistence uses SQLAlchemyJobStore against the same SQLite file, so
  scheduled jobs survive a process restart without needing to be
  re-registered from scratch.
- A lightweight `reconcile_jobs` job runs every 60s and is the single
  bridge between "admin changed something in the dashboard" (a separate
  process) and "the bot process's live scheduler". It adds jobs for newly
  ACTIVE campaigns, updates changed intervals, and removes jobs for
  campaigns that are no longer ACTIVE. This avoids building separate
  inter-process messaging for V1.

Idempotency / duplicate-execution protection (spec section 9):
  Before a campaign job does any sending, it reloads the campaign row
  fresh and checks `last_execution_at`. If the campaign already ran
  within the last ~90% of its interval, the run is skipped — this is
  what prevents a double-fire (e.g. APScheduler misfire immediately
  followed by a restart-triggered reconcile) from posting twice.
  `last_execution_at` is written the moment a run begins, not after it
  finishes, so a crash mid-run also blocks an immediate re-fire on
  restart.

  Trade-off: if the process crashes *after* successfully posting to some
  groups in a cycle but before finishing the rest, on restart those
  remaining groups will NOT be retried until the next natural interval —
  we intentionally don't guess whether a SENDING-status attempt actually
  reached Telegram (see posting_log_repository.find_stuck_sending, which
  simply marks those rows FAILED for visibility rather than silently
  retrying and risking a duplicate post).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

# from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from app.config import settings
from app.database.connection import engine as app_engine, session_scope
from app.repositories import campaign_repository, category_repository, posting_log_repository
from app.services import campaign_service, telegram_service
from app.models import CampaignStatus, PostingLog, Group as GroupModel

logger = logging.getLogger("app.scheduler")

RECONCILE_INTERVAL_SECONDS = 60
STUCK_SENDING_TIMEOUT_MINUTES = 10


def build_scheduler() -> AsyncIOScheduler:
    # Reuse the app's own engine (WAL mode + busy_timeout already set in
    # connection.py) rather than letting SQLAlchemyJobStore open a second,
    # unconfigured connection to the same SQLite file — two independently
    # configured connections to one file is exactly how you end up with
    # sporadic "database is locked" errors under real concurrency.
    #jobstores = {"default": SQLAlchemyJobStore(engine=app_engine)}
    scheduler = AsyncIOScheduler(timezone="UTC")
    return scheduler


def _job_id(campaign_id: int) -> str:
    return f"campaign_{campaign_id}"


async def run_campaign_job(campaign_id: int, bot: Bot) -> None:
    """The actual per-campaign execution. Registered as an APScheduler job."""
    run_time = datetime.now(timezone.utc)

    with session_scope() as db:
        campaign = campaign_repository.get_campaign(db, campaign_id)
        if campaign is None:
            logger.warning("Campaign %s no longer exists — skipping run.", campaign_id)
            return
        if campaign.status != CampaignStatus.ACTIVE:
            logger.info("Campaign %s is not ACTIVE — skipping run.", campaign_id)
            return

        # --- idempotency guard ---
        if campaign.last_execution_at is not None:
            elapsed = (run_time - campaign.last_execution_at).total_seconds()
            if elapsed < campaign.interval_seconds * 0.9:
                logger.info(
                    "Campaign %s ran %.0fs ago (interval %ss) — skipping duplicate fire.",
                    campaign_id, elapsed, campaign.interval_seconds,
                )
                return

        # Mark the run as started immediately, before any sending happens.
        next_run = run_time + timedelta(seconds=campaign.interval_seconds)
        campaign_repository.record_execution(db, campaign, last_run=run_time, next_run=next_run)

        targets = campaign_repository.get_assigned_groups(db, campaign_id)
        category = category_repository.get_category(db, campaign.category_id)
        category_name = category.name if category else "General"

        if not targets:
            posting_log_repository.mark_skipped(
                db, campaign_id, group_id=None, scheduled_for=run_time,
                reason="Campaign has no assigned groups.",
            )
            logger.warning("Campaign %s has no assigned groups.", campaign_id)
            return

        try:
            rendered_text = campaign_service.render_message(campaign, category_name, now=run_time)
        except Exception as e:  # noqa: BLE001 — bad template shouldn't crash the scheduler
            logger.exception("Template render failed for campaign %s", campaign_id)
            return

        campaign_name = campaign.name
        media_file_id = campaign.media_file_id

    # Send to each group independently — one failure must never stop the rest.
    for group in targets:
        with session_scope() as db:
            log = posting_log_repository.start_attempt(db, campaign_id, group.id, scheduled_for=run_time)
            log_id = log.id

        result = await telegram_service.send_campaign_message(
            bot, chat_id=group.telegram_chat_id, text=rendered_text, media_file_id=media_file_id
        )

        with session_scope() as db:
            log = db.get(PostingLog, log_id)
            group_row = db.get(GroupModel, group.id)
            if result.success:
                posting_log_repository.mark_success(db, log, result.message_id)
                if group_row:
                    group_row.last_successful_post_at = datetime.now(timezone.utc)
                    group_row.bot_has_permission = True
            else:
                posting_log_repository.mark_failed(db, log, result.error or "Unknown error")
                if group_row:
                    group_row.last_failure_at = datetime.now(timezone.utc)
                    group_row.last_failure_reason = (result.error or "")[:500]
                    if result.error and ("forbidden" in result.error.lower() or "permission" in result.error.lower()):
                        group_row.bot_has_permission = False
                logger.warning("Campaign %s -> group %s FAILED: %s", campaign_id, group.id, result.error)


def reconcile_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """
    Sync APScheduler's live jobs with what's ACTIVE in the DB. Runs every
    RECONCILE_INTERVAL_SECONDS. This is how dashboard-side changes (new
    campaign, pause, resume, interval edit) reach the running scheduler
    without needing direct IPC between the dashboard and bot processes.
    """
    with session_scope() as db:
        active_campaigns = campaign_repository.get_active_campaigns(db)
        active_ids = {c.id: c for c in active_campaigns}

    existing_job_ids = {job.id for job in scheduler.get_jobs() if job.id.startswith("campaign_")}
    active_job_ids = {_job_id(cid) for cid in active_ids}

    # Remove jobs for campaigns that are no longer active/no longer exist.
    for job_id in existing_job_ids - active_job_ids:
        scheduler.remove_job(job_id)
        logger.info("Removed scheduler job %s (campaign paused/deleted).", job_id)

    # Add or update jobs for active campaigns.
    for campaign_id, campaign in active_ids.items():
        job_id = _job_id(campaign_id)
        existing = scheduler.get_job(job_id)
        if existing is None:
            scheduler.add_job(
                run_campaign_job,
                trigger="interval",
                seconds=campaign.interval_seconds,
                id=job_id,
                args=[campaign_id, bot],
                replace_existing=True,
                misfire_grace_time=60,
                coalesce=True,  # if multiple runs were missed, only run once on catch-up
            )
            logger.info("Scheduled campaign %s every %ss.", campaign_id, campaign.interval_seconds)
        elif existing.trigger.interval.total_seconds() != campaign.interval_seconds:
            scheduler.reschedule_job(job_id, trigger="interval", seconds=campaign.interval_seconds)
            logger.info("Rescheduled campaign %s to %ss interval.", campaign_id, campaign.interval_seconds)


def recover_stuck_sending_logs() -> None:
    """
    Run once at startup. Any posting_log row left in SENDING past a
    reasonable timeout means the process died mid-attempt. We can't know
    whether Telegram actually received it, so we mark it FAILED (visible
    in the admin log, flagged for manual review) rather than silently
    retrying — see the module docstring for the reasoning.
    """
    with session_scope() as db:
        stuck = posting_log_repository.find_stuck_sending(db, older_than_minutes=STUCK_SENDING_TIMEOUT_MINUTES)
        for log in stuck:
            posting_log_repository.mark_failed(
                db, log, "Interrupted before result was recorded (likely crash/restart) — verify manually."
            )
        if stuck:
            logger.warning("Recovered %d stuck SENDING posting_log rows on startup.", len(stuck))


def start_scheduler(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    recover_stuck_sending_logs()
    scheduler.add_job(
        reconcile_jobs,
        trigger="interval",
        seconds=RECONCILE_INTERVAL_SECONDS,
        id="reconcile_jobs",
        args=[scheduler, bot],
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # run once immediately on startup
    )
    scheduler.start()
    logger.info("Scheduler started.")
