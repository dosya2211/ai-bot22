# bot/logic.py
import asyncio
import inspect
import logging
from typing import Dict, Any, Optional
from bot.services.llm_g4f import LLM
from bot.services.memory import Memory

logger = logging.getLogger(__name__)

llm = LLM()
memory = Memory()

def build_system_prompt(role: str, policy_text: Optional[str]) -> str:
    safe_policy = policy_text or ""
    return (
        "Ты помощник внутри CRM агентства недвижимости. "
        "Строго следуй инструкции и бизнес-логике. "
        "Всегда спрашивай подтверждение перед изменениями в БД. "
        f"Твоя роль: {role}. Инструкция:\n{safe_policy[:6000]}"
    )

async def _maybe_await(value):
    if inspect.isawaitable(value) or asyncio.iscoroutine(value):
        return await value
    return value

async def ai_reply(role: str, user_text: str, policy_text: Optional[str]) -> str:
    sys = build_system_prompt(role, policy_text)
    try:
        res = llm.chat([
            {"role": "system", "content": sys},
            {"role": "user", "content": user_text}
        ])
        answer = await _maybe_await(res)
        if answer is None:
            return "Извините, ИИ не вернул ответ."
        return str(answer)
    except Exception as e:
        logger.exception("LLM chat error")
        return f"⚠️ Ошибка при обращении к ИИ: {e}"

async def remember(user_id: int, role: str, text: str, meta: Dict[str, Any]):
    try:
        res = memory.upsert_dialog(user_id, role, text, meta)
        await _maybe_await(res)
    except Exception as e:
        logger.exception("Memory upsert error")
