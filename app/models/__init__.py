"""
Import every model module here so that `Base.metadata.create_all()` (called
from app.database.connection) discovers all tables, and so other modules can
do `from app.models import Category, Group, ...`.
"""
from app.models.base import Base
from app.models.category import Category
from app.models.group import Group, GroupCategory
from app.models.campaign import Campaign, CampaignGroup, CampaignStatus
from app.models.posting_log import PostingLog, PostingStatus
from app.models.service import Service, ServicePackage
from app.models.user import User
from app.models.order import Order, Payment, OrderStatus, PaymentVerificationStatus
from app.models.settings import AppSetting

__all__ = [
    "Base",
    "Category",
    "Group",
    "GroupCategory",
    "Campaign",
    "CampaignGroup",
    "CampaignStatus",
    "PostingLog",
    "PostingStatus",
    "Service",
    "ServicePackage",
    "User",
    "Order",
    "Payment",
    "OrderStatus",
    "PaymentVerificationStatus",
    "AppSetting",
]
