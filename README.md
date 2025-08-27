# Telegram AI CRM Bot (Docker, Baserow, Qdrant, Redis, Kokoro TTS, GPT4Free)

Полнофункциональный Telegram-бот CRM для АН «Типаж». 
- Inline-меню и навигация по таблицам Baserow
- Диалог с ИИ (GPT4Free) с учетом должностной инструкции
- Векторная память (Qdrant + sentence-transformers)
- Сессии и кеш (Redis)
- Синтез речи (Kokoro FastAPI, OpenAI-совместимый /v1/audio/speech)
- Роли: Сотрудник / Руководитель
- Чек-ин/чек-аут, ежедневные отчеты и финансы

## Быстрый старт

1. Создайте .env в корне проекта (см. пример в `.env.example`).
2. Убедитесь, что у вас есть Telegram Bot Token.
3. Запустите:
   ```bash
   docker compose up --build -d
   ```
4. Откройте чат с ботом и введите `/start`.

## Инициализация Baserow

Впишите `BASEROW_JWT` и `BASEROW_DATABASE_ID` в .env. При старте бот создаст необходимые таблицы и поля.

## Примечания по ИИ и векторной памяти

- По умолчанию используется модель эмбеддингов `sentence-transformers/all-MiniLM-L6-v2`.
- Если загрузка модели недоступна, бот переключится на резервный простейший хеш-векторизатор.
