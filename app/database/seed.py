"""
Optional starter data. Run with: python -m app.database.seed

Only inserts categories that don't already exist (by name) — safe to
re-run. These are just a starting point; admins can add/edit/deactivate
categories from the dashboard afterward (spec section 6 — nothing here is
hardcoded into business logic, this is just convenience seed data).
"""
from __future__ import annotations

from app.database.connection import init_db, session_scope
from app.models import Category

STARTER_CATEGORIES = [
    ("SMM", "General social media marketing services", "📱"),
    ("Instagram", "Instagram-related services", "📸"),
    ("Facebook", "Facebook-related services", "📘"),
    ("Snapchat", "Snapchat-related services", "👻"),
    ("YouTube", "YouTube-related services", "▶️"),
    ("TikTok", "TikTok-related services", "🎵"),
    ("Telegram", "Telegram-related services", "📱"),
    ("X / Twitter", "X (Twitter)-related services", "🐦"),
    ("Other Services", "Anything that doesn't fit another category", "🔧"),
]


def run() -> None:
    init_db()
    with session_scope() as db:
        existing = {c.name for c in db.query(Category).all()}
        created = 0
        for name, description, icon in STARTER_CATEGORIES:
            if name in existing:
                continue
            db.add(Category(name=name, description=description, icon=icon, is_active=True))
            created += 1
        print(f"Seed complete. {created} new categories created, {len(existing)} already existed.")


if __name__ == "__main__":
    run()
