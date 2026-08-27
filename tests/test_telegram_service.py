from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut

from app.services.telegram_service import send_campaign_message


class FakeMessage:
    message_id = 12345


@pytest.mark.asyncio
async def test_send_success():
    bot = AsyncMock()
    bot.send_message.return_value = FakeMessage()
    result = await send_campaign_message(bot, chat_id=-100123, text="hello")
    assert result.success is True
    assert result.message_id == 12345


@pytest.mark.asyncio
async def test_send_success_with_media():
    bot = AsyncMock()
    bot.send_photo.return_value = FakeMessage()
    result = await send_campaign_message(bot, chat_id=-100123, text="caption", media_file_id="FILE_ID")
    assert result.success is True
    bot.send_photo.assert_called_once()


@pytest.mark.asyncio
async def test_send_forbidden_permission_error():
    bot = AsyncMock()
    bot.send_message.side_effect = Forbidden("bot was kicked from the group chat")
    result = await send_campaign_message(bot, chat_id=-100123, text="hi")
    assert result.success is False
    assert "Forbidden" in result.error


@pytest.mark.asyncio
async def test_send_bad_request_chat_not_found():
    bot = AsyncMock()
    bot.send_message.side_effect = BadRequest("Chat not found")
    result = await send_campaign_message(bot, chat_id=-100123, text="hi")
    assert result.success is False
    assert "Bad request" in result.error


@pytest.mark.asyncio
async def test_send_rate_limited():
    bot = AsyncMock()
    bot.send_message.side_effect = RetryAfter(30)
    result = await send_campaign_message(bot, chat_id=-100123, text="hi")
    assert result.success is False
    assert "Rate limited" in result.error


@pytest.mark.asyncio
async def test_send_network_error():
    bot = AsyncMock()
    bot.send_message.side_effect = NetworkError("connection reset")
    result = await send_campaign_message(bot, chat_id=-100123, text="hi")
    assert result.success is False
    assert "Network" in result.error


@pytest.mark.asyncio
async def test_send_timeout():
    bot = AsyncMock()
    bot.send_message.side_effect = TimedOut()
    result = await send_campaign_message(bot, chat_id=-100123, text="hi")
    assert result.success is False


@pytest.mark.asyncio
async def test_send_unexpected_exception_never_propagates():
    """A single group's unexpected failure must never raise out of this call —
    that's what lets the scheduler continue to the next group."""
    bot = AsyncMock()
    bot.send_message.side_effect = RuntimeError("something truly unexpected")
    result = await send_campaign_message(bot, chat_id=-100123, text="hi")
    assert result.success is False
    assert "Unexpected error" in result.error
