from typing import Dict, Any
from bot.services.llm_g4f import LLM
from bot.services.memory import Memory

llm = LLM()
memory = Memory()


def build_system_prompt(role: str, policy_text: str) -> str:
    """Формируем системный prompt для LLM"""
    safe_policy = policy_text or ""
    return (
        "Ты помощник внутри CRM агентства недвижимости. "
        "Строго следуй инструкции и бизнес-логике. "
        "Всегда спрашивай подтверждение перед изменениями в БД. "
        f"Твоя роль: {role}. Инструкция:\n{safe_policy[:6000]}"
    )


async def ai_reply(role: str, user_text: str, policy_text: str) -> str:
    """Генерация ответа через LLM"""
    sys = build_system_prompt(role, policy_text)
    try:
        answer = await llm.chat([
            {"role": "system", "content": sys},
            {"role": "user", "content": user_text}
        ])
    except Exception as e:
        answer = f"⚠️ Ошибка при обращении к ИИ: {e}"
    return answer


async def remember(user_id: int, role: str, text: str, meta: Dict[str, Any]):
    """Сохраняем контекст диалога в памяти"""
    try:
        await memory.upsert_dialog(user_id, role, text, meta)
    except Exception as e:
        # Логируем ошибку, чтобы бот не падал
        print(f"[MemoryError] {e}")
