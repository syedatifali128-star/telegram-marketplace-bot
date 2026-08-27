from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """
    A configurable category (e.g. Instagram, SMM, YouTube).

    Categories are admin-managed data, never hardcoded into business logic.
    They tie together marketplace groups, campaigns, and customer-facing
    services.
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    icon: Mapped[str | None] = mapped_column(String(20))  # emoji
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    groups: Mapped[list["GroupCategory"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="category")
    services: Mapped[list["Service"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r} active={self.is_active}>"
