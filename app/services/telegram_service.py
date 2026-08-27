from __future__ import annotations

import logging

from telegram import Bot
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TelegramError, TimedOut

logger = logging.getLogger("app.services.telegram")


class SendResult:
    def __init__(self, success: bool, message_id: int | None = None, error: str | None = None):
        self.success = success
        self.message_id = message_id
        self.error = error


async def send_campaign_message(bot: Bot, chat_id: int, text: str, media_file_id: str | None = None) -> SendResult:
    """
    Send one campaign message to one group. Every Telegram-side failure
    mode is caught here and turned into a SendResult rather than an
    uncaught exception, so the scheduler can log it and move on to the
    next group without dying (spec sections 8 & 10).
    """
    try:
        if media_file_id:
            message = await bot.send_photo(chat_id=chat_id, photo=media_file_id, caption=text)
        else:
            message = await bot.send_message(chat_id=chat_id, text=text)
        return SendResult(success=True, message_id=message.message_id)

    except RetryAfter as e:
        # Telegram's own rate-limit response — surface it plainly, don't retry inline.
        return SendResult(success=False, error=f"Rate limited by Telegram, retry after {e.retry_after}s")
    except Forbidden as e:
        # Bot kicked, blocked, or lacks permission to post in this chat.
        return SendResult(success=False, error=f"Forbidden / insufficient permission: {e}")
    except BadRequest as e:
        # Chat not found, message rejected, invalid formatting, etc.
        return SendResult(success=False, error=f"Bad request: {e}")
    except (NetworkError, TimedOut) as e:
        return SendResult(success=False, error=f"Network/timeout error: {e}")
    except TelegramError as e:
        return SendResult(success=False, error=f"Telegram API error: {e}")
    except Exception as e:  # noqa: BLE001 — last-resort catch so one bad group never kills the run
        logger.exception("Unexpected error sending to chat_id=%s", chat_id)
        return SendResult(success=False, error=f"Unexpected error: {e}")
