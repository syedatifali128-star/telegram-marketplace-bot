from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Service(Base, TimestampMixin):
    """A customer-facing service under a category (e.g. 'Followers' under Instagram)."""
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category"] = relationship(back_populates="services")
    packages: Mapped[list["ServicePackage"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r}>"


class ServicePackage(Base, TimestampMixin):
    """A concrete quantity/price package under a service (e.g. '1K — $2')."""
    __tablename__ = "service_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "1K"
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    service: Mapped["Service"] = relationship(back_populates="packages")

    def __repr__(self) -> str:
        return f"<ServicePackage id={self.id} label={self.label!r} price={self.price}>"
