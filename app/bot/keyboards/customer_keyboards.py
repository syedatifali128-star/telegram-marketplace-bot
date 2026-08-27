from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import Category, Service, ServicePackage

# Callback data is kept short and namespaced: "<action>:<id>"
# e.g. "cat:3", "svc:12", "pkg:44", "order:44", "back:home"


def categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for cat in categories:
        label = f"{cat.icon or ''} {cat.name}".strip()
        row.append(InlineKeyboardButton(label, callback_data=f"cat:{cat.id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton("🛒 My Orders", callback_data="myorders"),
            InlineKeyboardButton("💬 Support", callback_data="support"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def services_keyboard(services: list[Service], category_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(svc.name, callback_data=f"svc:{svc.id}")] for svc in services]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="back:home")])
    return InlineKeyboardMarkup(rows)


def packages_keyboard(packages: list[ServicePackage], service_id: int, category_id: int) -> InlineKeyboardMarkup:
    rows = []
    for pkg in packages:
        label = f"{pkg.label} — ${pkg.price}"
        rows.append([InlineKeyboardButton(label, callback_data=f"pkg:{pkg.id}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"cat:{category_id}")])
    return InlineKeyboardMarkup(rows)


def package_detail_keyboard(package: ServicePackage, service_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛒 Order", callback_data=f"order:{package.id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"svc:{service_id}")],
        ]
    )


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to menu", callback_data="back:home")]])
