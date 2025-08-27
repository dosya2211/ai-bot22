# bot/auth.py
from functools import wraps
from aiogram import types
from bot.config import MANAGER_TELEGRAM_ID
import logging

logger = logging.getLogger(__name__)

def manager_only(func):
    @wraps(func)
    async def wrapper(obj, *args, **kwargs):
        user_id = None
        # Message or CallbackQuery
        if isinstance(obj, types.Message):
            user_id = obj.from_user.id
        elif isinstance(obj, types.CallbackQuery):
            user_id = obj.from_user.id
        else:
            # If wrapper used on other handlers, try to extract first arg
            try:
                maybe = args[0]
                if hasattr(maybe, "from_user"):
                    user_id = maybe.from_user.id
            except Exception:
                user_id = None

        if user_id != MANAGER_TELEGRAM_ID:
            try:
                # both Message and CallbackQuery have .answer
                await obj.answer("Доступ запрещен: только руководитель.", show_alert=True)
            except Exception:
                logger.exception("Failed to send manager_only response")
            return
        return await func(obj, *args, **kwargs)
    return wrapper
