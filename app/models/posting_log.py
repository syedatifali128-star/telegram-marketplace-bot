from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PostingStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class PostingLog(Base, TimestampMixin):
    """
    One row per (campaign, group, scheduled execution) attempt.

    A row is written as PENDING/SENDING *before* the Telegram call is made,
    then updated to SUCCESS/FAILED/SKIPPED after. This is what lets the app
    detect "was this already sent?" after an unclean restart — see
    scheduler_service for the recovery logic that reads this table.
    """
    __tablename__ = "posting_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    # Nullable to allow campaign-level log entries (e.g. "no groups assigned")
    # that aren't about any specific group.
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True)

    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[PostingStatus] = mapped_column(
        Enum(PostingStatus), default=PostingStatus.PENDING, nullable=False
    )
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="posting_logs")
    group: Mapped["Group"] = relationship()

    def __repr__(self) -> str:
        return f"<PostingLog id={self.id} campaign={self.campaign_id} group={self.group_id} status={self.status}>"
