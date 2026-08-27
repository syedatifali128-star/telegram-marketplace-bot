from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentVerificationStatus(str, enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    service_package_id: Mapped[int] = mapped_column(ForeignKey("service_packages.id"), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    target: Mapped[str] = mapped_column(String(300), nullable=False)  # e.g. profile link/handle
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="orders")
    service_package: Mapped["ServicePackage"] = relationship()
    payment: Mapped["Payment | None"] = relationship(
        back_populates="order", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} user={self.user_id} status={self.status}>"


class Payment(Base, TimestampMixin):
    """
    A customer's payment submission for an order.

    CRITICAL: submitting a reference/UTR here never auto-marks the order as
    paid. verification_status starts (and stays) PENDING_VERIFICATION until
    an admin explicitly verifies it via the dashboard. See order_service.
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[str | None] = mapped_column(String(100))  # e.g. "UPI", "Bank transfer"
    reference: Mapped[str | None] = mapped_column(String(200))  # UTR / txn ref customer entered
    proof_file_id: Mapped[str | None] = mapped_column(String(300))  # Telegram file_id of screenshot

    verification_status: Mapped[PaymentVerificationStatus] = mapped_column(
        Enum(PaymentVerificationStatus),
        default=PaymentVerificationStatus.PENDING_VERIFICATION,
        nullable=False,
    )
    verified_by: Mapped[str | None] = mapped_column(String(100))  # admin username
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admin_notes: Mapped[str | None] = mapped_column(Text)

    order: Mapped["Order"] = relationship(back_populates="payment")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} order={self.order_id} status={self.verification_status}>"
