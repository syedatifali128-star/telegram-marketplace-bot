from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CampaignStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class Campaign(Base, TimestampMixin):
    """
    A configured advertisement + schedule + target group set.

    IMPORTANT: a campaign never resolves its targets by category lookup at
    send time. Targets are the explicit rows in `campaign_groups` only —
    that is the isolation boundary between e.g. Instagram and Facebook
    campaigns. See CampaignGroup below.
    """
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    media_file_id: Mapped[str | None] = mapped_column(String(300))  # Telegram file_id, optional

    # Interval-based scheduling for V1 (e.g. every N minutes/hours).
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)

    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.PAUSED, nullable=False
    )

    last_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped["Category"] = relationship(back_populates="campaigns")
    group_links: Mapped[list["CampaignGroup"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    posting_logs: Mapped[list["PostingLog"]] = relationship(back_populates="campaign")

    def __repr__(self) -> str:
        return f"<Campaign id={self.id} name={self.name!r} status={self.status}>"


class CampaignGroup(Base, TimestampMixin):
    """
    Explicit campaign -> group assignment.

    This is the ONLY source of truth the scheduler uses to determine where
    a campaign is allowed to post. A campaign with no rows here posts
    nowhere, by design — there is no implicit "post to all groups in my
    category" fallback.
    """
    __tablename__ = "campaign_groups"
    __table_args__ = (UniqueConstraint("campaign_id", "group_id", name="uq_campaign_group"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="group_links")
    group: Mapped["Group"] = relationship(back_populates="campaign_links")
