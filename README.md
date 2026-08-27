# Telegram Marketplace Manager

A centralized system for:
1. **Automated, authorized advertisement posting** to configured Telegram marketplace groups on a schedule.
2. **A customer-facing bot menu** to browse services and place orders (manual payment verification).

Built for use with groups/accounts you are authorized to manage. No spam-evasion, ban-evasion, CAPTCHA bypass, or unauthorized-access functionality is included or supported.

---

## 1. Requirements

- Python 3.12+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- (Optional but recommended for deployment) Docker + Docker Compose

## 2. Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Edit `.env`:
- `BOT_TOKEN` — from @BotFather
- `ADMIN_TELEGRAM_IDS` — your numeric Telegram ID (from @userinfobot), comma-separated if more than one
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — your dashboard login (change the default password)

Initialize the database (creates `data/app.db` and starter categories):
```bash
python -m app.database.seed
```

Run the dashboard (web admin) and the bot as **two separate processes**:
```bash
# terminal 1
python -m app.main            # dashboard at http://localhost:8000

# terminal 2
python -m app.bot.run_bot     # Telegram bot + scheduler
```

Log into the dashboard at `http://localhost:8000/login` with the credentials from `.env`.

## 3. Running tests

```bash
pytest
```

Tests use an isolated in-memory SQLite database and a mocked Telegram `Bot` — no real Telegram messages are sent and nothing touches `data/app.db`.

## 4. Docker deployment (VPS)

```bash
cp .env.example .env   # fill it in as above
docker compose up -d --build
```

This starts two containers from one image: `dashboard` (web admin, port from `APP_PORT`) and `bot` (polling + scheduler), both sharing the same `data/` volume.

Check logs:
```bash
docker compose logs -f bot
docker compose logs -f dashboard
```

Restart after a crash or server reboot:
```bash
docker compose up -d
```
Both services have `restart: unless-stopped`, so Docker restarts them automatically after a VPS reboot as long as Docker itself is set to start on boot (`sudo systemctl enable docker`).

## 5. Backups

```bash
./backup.sh
```
Writes a timestamped copy of `data/app.db` into `backups/`, using SQLite's online `.backup` command (safe to run while the app is live). Keeps the last 30 backups. Add it to cron for automatic hourly/daily backups.

## 6. How it works (short version)

- **Categories** (Instagram, SMM, etc.) are admin-managed, not hardcoded.
- **Groups** are added via the dashboard with a Telegram chat ID and one or more categories.
- **Campaigns** have a message, an interval, and an explicit list of **assigned groups** — a campaign never posts anywhere it wasn't explicitly assigned to, regardless of category.
- The **scheduler** (APScheduler, running inside the bot process) fires each active campaign on its interval, logs every attempt (`PENDING → SENDING → SUCCESS/FAILED/SKIPPED`) to `posting_logs`, and never lets one group's failure stop the others.
- **Duplicate-post protection**: each campaign's `last_execution_at` is written the moment a run starts; a run that would fire again too soon after the last one is skipped. Rows stuck in `SENDING` after a crash are flagged for manual review on the next startup rather than silently retried.
- **Payments** are never auto-confirmed. A customer's submitted reference/UTR sits as `PENDING_VERIFICATION` until an admin explicitly approves or rejects it in the dashboard.

## 7. Project structure

```
app/
  main.py              FastAPI entrypoint (dashboard/API)
  config.py            Env-based settings
  database/            Engine, session, seed data
  models/               SQLAlchemy models (10 tables)
  repositories/         DB query layer
  services/              Business logic (validation, scheduling, sending)
  bot/
    run_bot.py          Bot process entrypoint (polling + scheduler)
    handlers/            Customer-facing conversation handlers
    keyboards/           Inline keyboard builders
  dashboard/            Admin web UI (FastAPI routes + Jinja2 templates)
  core/security.py      Dashboard session auth
tests/                 Pytest suite (mocked Telegram, isolated DB)
data/                  SQLite database file (gitignored)
logs/                  App logs (gitignored)
backup.sh              SQLite backup script
Dockerfile / docker-compose.yml
```

## 8. What's intentionally NOT in V1

- Automated payment gateway integration (manual verification only)
- Webhook mode for the bot (polling only — simpler for a first VPS deploy)
- PostgreSQL (SQLite is sufficient at this scale; models use standard SQLAlchemy so migrating later doesn't require a rewrite)
- Multi-admin roles/permissions (single admin login via `.env`)
- Automatic retry-with-backoff for failed sends (failures are logged for manual review, not silently retried, to avoid accidental duplicate posts)

## 9. Known limitations to review before production

- **No CSRF tokens on dashboard forms.** `SameSite=Lax` cookies provide baseline protection, but if you expose the dashboard beyond a trusted network, add CSRF middleware (e.g. `starlette-csrf`) before going further.
- **SQLite is single-file, multi-process.** WAL mode + `busy_timeout` are enabled (see `app/database/connection.py`) so the dashboard and bot processes don't collide, but very high write volume would eventually want Postgres — the ORM layer doesn't need to change, just `DATABASE_URL`.
- **`requirements.txt` versions were written from general knowledge, not verified against PyPI from this environment** (no network access here). Run `pip install -r requirements.txt` on your machine first and loosen any pin that fails to resolve.
- **No automated retry for failed sends.** A failed group is logged, not retried — intentional (see section 6 above), but means a transient network blip requires the next scheduled interval to self-heal.
