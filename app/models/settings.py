from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AppSetting(Base, TimestampMixin):
    """
    Simple key-value store for global settings that don't deserve their own
    table (e.g. "scheduler_globally_paused" = "true"). Deliberately generic
    but only used for small config flags — not for storing structured
    application state.
    """
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
