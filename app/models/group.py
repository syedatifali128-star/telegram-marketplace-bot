from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Group(Base, TimestampMixin):
    """
    A Telegram marketplace group the bot is authorized to post into.

    Groups are pure configuration data — addable/editable from the admin
    dashboard without touching code.
    """
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    username_or_link: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Permission/status info the scheduler updates after send attempts.
    bot_has_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_successful_post_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_reason: Mapped[str | None] = mapped_column(String(500))

    categories: Mapped[list["GroupCategory"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    campaign_links: Mapped[list["CampaignGroup"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r} chat_id={self.telegram_chat_id}>"


class GroupCategory(Base):
    """
    Many-to-many link: a group can legitimately serve more than one category
    (e.g. a general SMM group that also accepts Instagram ads).
    This table is READ from when validating campaign targets — see
    CampaignGroup for the actual per-campaign explicit assignment, which is
    the real isolation boundary.
    """
    __tablename__ = "group_categories"
    __table_args__ = (UniqueConstraint("group_id", "category_id", name="uq_group_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    group: Mapped["Group"] = relationship(back_populates="categories")
    category: Mapped["Category"] = relationship(back_populates="groups")
