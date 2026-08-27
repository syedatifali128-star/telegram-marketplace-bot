"""
Central application configuration.

Everything here is loaded from environment variables (via .env in local
development). No secrets are ever hardcoded — see .env.example for the
full list of variables this app expects.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    bot_token: str = ""
    admin_telegram_ids: str = ""  # comma-separated, parsed via `admin_ids` property

    # --- Database ---
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"

    # --- Dashboard / security ---
    secret_key: str = "insecure-dev-key-change-me"
    admin_username: str = "admin"
    admin_password: str = "change-me"

    # --- App ---
    app_env: str = "development"
    app_port: int = 8000
    default_timezone: str = "Asia/Kolkata"

    # --- Logging ---
    log_level: str = "INFO"
    log_file: str = str(BASE_DIR / "logs" / "app.log")

    @property
    def admin_ids(self) -> list[int]:
        """Parse ADMIN_TELEGRAM_IDS into a list of ints, ignoring blanks/junk."""
        ids: list[int] = []
        for raw in self.admin_telegram_ids.split(","):
            raw = raw.strip()
            if raw.isdigit():
                ids.append(int(raw))
        return ids

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()

# Ensure runtime directories exist regardless of where the app is launched from.
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
