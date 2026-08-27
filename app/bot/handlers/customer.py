from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.database.connection import session_scope
from app.repositories import order_repository, user_repository
from app.services import catalog_service, order_service
from app.bot.keyboards import customer_keyboards as kb

logger = logging.getLogger("app.bot.customer")

WELCOME_TEXT = (
    "🚀 *Welcome to our marketplace*\n\n"
    "Choose a platform below to see available services."
)

SUPPORT_TEXT = "💬 Need help? Message the admin directly and we'll get back to you shortly."

# context.user_data keys used for the simple order flow state machine
AWAITING_TARGET = "awaiting_target_for_package_id"
AWAITING_PAYMENT_REF = "awaiting_payment_ref_for_order_id"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    with session_scope() as db:
        user_repository.get_or_create_user(
            db, telegram_user_id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name
        )
        categories = catalog_service.list_categories(db)
    if not categories:
        await update.message.reply_text(
            "No services are configured yet — please check back soon."
        )
        return
    await update.message.reply_text(
        WELCOME_TEXT, parse_mode="Markdown", reply_markup=kb.categories_keyboard(categories)
    )


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    with session_scope() as db:
        categories = catalog_service.list_categories(db)
    await query.edit_message_text(
        WELCOME_TEXT, parse_mode="Markdown", reply_markup=kb.categories_keyboard(categories)
    )


async def show_services(update: Update, context: ContextTypes.DEFAULT_TYPE, category_id: int) -> None:
    query = update.callback_query
    with session_scope() as db:
        category = catalog_service.get_category_or_none(db, category_id)
        if category is None:
            await query.edit_message_text("This category is no longer available.", reply_markup=kb.back_home_keyboard())
            return
        services = catalog_service.list_services(db, category_id)
    if not services:
        await query.edit_message_text(
            f"No services available under {category.name} right now.",
            reply_markup=kb.back_home_keyboard(),
        )
        return
    text = f"{category.icon or ''} *{category.name}*\n\nChoose a service:".strip()
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.services_keyboard(services, category_id))


async def show_packages(update: Update, context: ContextTypes.DEFAULT_TYPE, service_id: int) -> None:
    query = update.callback_query
    with session_scope() as db:
        service = catalog_service.get_service_or_none(db, service_id)
        if service is None:
            await query.edit_message_text("This service is no longer available.", reply_markup=kb.back_home_keyboard())
            return
        packages = catalog_service.list_packages(db, service_id)
        category_id = service.category_id
    if not packages:
        await query.edit_message_text(
            f"No packages available for {service.name} right now.", reply_markup=kb.back_home_keyboard()
        )
        return
    text = f"*{service.name}*\n\n{service.description or ''}\n\nChoose a package:".strip()
    await query.edit_message_text(
        text, parse_mode="Markdown", reply_markup=kb.packages_keyboard(packages, service_id, category_id)
    )


async def show_package_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, package_id: int) -> None:
    query = update.callback_query
    with session_scope() as db:
        package = catalog_service.get_package_or_none(db, package_id)
        if package is None:
            await query.edit_message_text("This package is no longer available.", reply_markup=kb.back_home_keyboard())
            return
        service = catalog_service.get_service_or_none(db, package.service_id)
    text = (
        f"*{service.name}*\n\n"
        f"{package.label} — *${package.price} {package.currency}*\n\n"
        f"Tap Order to proceed."
    )
    await query.edit_message_text(
        text, parse_mode="Markdown", reply_markup=kb.package_detail_keyboard(package, package.service_id)
    )


async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE, package_id: int) -> None:
    query = update.callback_query
    with session_scope() as db:
        package = catalog_service.get_package_or_none(db, package_id)
    if package is None:
        await query.edit_message_text("This package is no longer available.", reply_markup=kb.back_home_keyboard())
        return
    context.user_data[AWAITING_TARGET] = package_id
    await query.edit_message_text(
        "Please send the *target* for this order (e.g. your profile link or @username).\n\n"
        "Send /cancel to stop.",
        parse_mode="Markdown",
    )


async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg_user = update.effective_user
    with session_scope() as db:
        user = user_repository.get_user_by_telegram_id(db, tg_user.id)
        orders = order_service.get_my_orders(db, user) if user else []
        if not orders:
            await query.edit_message_text("You have no orders yet.", reply_markup=kb.back_home_keyboard())
            return
        lines = ["🛒 *Your orders*\n"]
        for o in orders[:10]:
            lines.append(f"#{o.id} — {o.status.value} — ${o.amount} {o.currency}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb.back_home_keyboard())


async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.edit_message_text(SUPPORT_TEXT, reply_markup=kb.back_home_keyboard())


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    try:
        action, _, raw_id = data.partition(":")
        entity_id = int(raw_id) if raw_id.isdigit() else None

        if data == "back:home" or action == "back" and raw_id == "home":
            await show_categories(update, context)
        elif action == "cat" and entity_id is not None:
            await show_services(update, context, entity_id)
        elif action == "svc" and entity_id is not None:
            await show_packages(update, context, entity_id)
        elif action == "pkg" and entity_id is not None:
            await show_package_detail(update, context, entity_id)
        elif action == "order" and entity_id is not None:
            await start_order(update, context, entity_id)
        elif data == "myorders":
            await show_my_orders(update, context)
        elif data == "support":
            await show_support(update, context)
        else:
            await query.edit_message_text("Unknown option.", reply_markup=kb.back_home_keyboard())
    except Exception:
        logger.exception("Error handling callback %s", data)
        await query.edit_message_text(
            "Something went wrong on our end — please try again.", reply_markup=kb.back_home_keyboard()
        )


async def text_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the two free-text steps in the order flow: target, then payment reference."""
    text = (update.message.text or "").strip()
    tg_user = update.effective_user

    if AWAITING_TARGET in context.user_data:
        package_id = context.user_data.pop(AWAITING_TARGET)
        with session_scope() as db:
            package = catalog_service.get_package_or_none(db, package_id)
            if package is None:
                await update.message.reply_text("That package is no longer available.")
                return
            user = user_repository.get_or_create_user(
                db, telegram_user_id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name
            )
            order = order_service.place_order(db, user=user, package=package, target=text)
            order_id = order.id
            amount = order.amount
            currency = order.currency
        context.user_data[AWAITING_PAYMENT_REF] = order_id
        await update.message.reply_text(
            f"✅ Order #{order_id} created — ${amount} {currency}.\n\n"
            "Please complete payment using the instructions provided by the admin, "
            "then reply here with your payment reference / UTR number.\n\n"
            "Your order will show as *pending verification* until an admin confirms it manually.",
            parse_mode="Markdown",
        )
        return

    if AWAITING_PAYMENT_REF in context.user_data:
        order_id = context.user_data.pop(AWAITING_PAYMENT_REF)
        with session_scope() as db:
            order = order_repository.get_order(db, order_id)
            if order is None:
                await update.message.reply_text("That order could not be found.")
                return
            order_service.submit_payment(db, order=order, reference=text)
        await update.message.reply_text(
            "📝 Payment reference received. Your order is *PENDING VERIFICATION* — "
            "an admin will confirm it shortly. You'll be notified once it's verified.",
            parse_mode="Markdown",
        )
        return

    # No active flow — nudge back to the menu instead of silently ignoring input.
    await update.message.reply_text("Use /start to open the menu.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(AWAITING_TARGET, None)
    context.user_data.pop(AWAITING_PAYMENT_REF, None)
    await update.message.reply_text("Cancelled. Use /start to open the menu again.")
