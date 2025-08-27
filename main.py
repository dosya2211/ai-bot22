# main.py (корень проекта или bot/main.py, в зависимости от структуры)
import asyncio
import logging
import datetime
import inspect
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import redis.asyncio as aioredis

from bot.config import TELEGRAM_TOKEN, REDIS_HOST, MANAGER_TELEGRAM_ID, validate_config
from bot.ui import main_menu, submenu
from bot.services.baserow_client import Baserow
from bot.logic import ai_reply, remember
from bot.policy_loader import load_policy_text
from bot.schema_full import TABLE_DEFINITIONS
from bot.services.tasks_service import TasksService
from bot.services.objects_service import ObjectsService
from bot.services.finance import FinanceService
from bot.services.memory import Memory
from bot.scheduler import start_scheduler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# validate required envs in prod
try:
    validate_config()
except Exception as e:
    logger.warning("Config validation failed: %s", e)
    # don't exit during dev/test; if you want strict prod, raise here
    # raise

baserow = Baserow()
policy_text = load_policy_text()
tasks_svc = TasksService(baserow)
objects_svc = ObjectsService(baserow)
finance_svc = FinanceService(baserow)
memory = Memory()

async def _maybe_await(value):
    if inspect.isawaitable(value) or asyncio.iscoroutine(value):
        return await value
    return value

async def ensure_tables_and_fields():
    try:
        res = baserow.list_tables()
        tables = await _maybe_await(res)
        existing = {t['name']: t['id'] for t in (tables or [])}
    except Exception as e:
        logger.exception("Failed to list baserow tables: %s", e)
        existing = {}

    for tbl_name, fields in TABLE_DEFINITIONS.items():
        if tbl_name not in existing:
            try:
                tid = baserow.create_table(tbl_name)
                tid = await _maybe_await(tid)
                if tid:
                    existing[tbl_name] = tid
            except Exception:
                logger.exception("Failed to create table %s", tbl_name)
                continue
        tid = existing.get(tbl_name)
        if not tid:
            continue
        for f in fields:
            try:
                r = baserow.ensure_field(tid, f['name'], f['type'])
                await _maybe_await(r)
            except Exception:
                logger.exception("Failed ensure_field %s on %s", f['name'], tbl_name)
                continue

async def on_startup(bot: Bot):
    await ensure_tables_and_fields()

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set. Exiting.")
        sys.exit(1)

    redis_pool = aioredis.from_url(f"redis://{REDIS_HOST}:6379", decode_responses=True)
    storage = RedisStorage(redis=redis_pool)
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=storage)

    loop = asyncio.get_event_loop()
    start_scheduler(loop, bot)

    @dp.message(F.command("start"))
    async def start_handler(m: Message):
        kb = main_menu()
        await m.answer("Выберите раздел (используйте inline-кнопки):", reply_markup=kb)

    @dp.callback_query(F.data == "back:main")
    async def back_main(c: CallbackQuery):
        await c.message.edit_text("Главное меню:", reply_markup=main_menu())

    @dp.callback_query(F.data.startswith("submenu:"))
    async def open_submenu(c: CallbackQuery):
        _, name = c.data.split(":", 1)
        await c.message.edit_text(f"{name}:", reply_markup=submenu(name))

    @dp.callback_query(F.data.startswith("table:"))
    async def open_table(c: CallbackQuery):
        _, tbl_name = c.data.split(":", 1)
        try:
            tid = baserow.get_table_id_by_name(tbl_name)
            tid = await _maybe_await(tid)
        except Exception:
            tid = None
        if not tid:
            await c.answer("Таблица не найдена", show_alert=True)
            return
        rows_res = baserow.list_rows(tid, size=100)
        rows_res = await _maybe_await(rows_res)
        rows = (rows_res or {}).get("results", []) if isinstance(rows_res, dict) else (rows_res or [])
        if not rows:
            await c.message.answer(f"Таблица «{tbl_name}» пуста.")
        else:
            lines = []
            for r in rows[:20]:
                lines.append(str({k: v for k, v in r.items() if not str(k).startswith('_')}))
            await c.message.answer(f"«{tbl_name}» (первые 20):\n" + "\n".join(lines))

    @dp.callback_query(F.data.startswith("action:"))
    async def submenu_action(c: CallbackQuery):
        _, group, action = c.data.split(":", 2)
        await c.message.answer(f"Вы выбрали: {group} → {action}. Напишите детали (одним сообщением).")
        await redis_pool.set(f"await_details:{c.from_user.id}", f"{group}|{action}", ex=600)

    @dp.message(F.text)
    async def text_handler(m: Message):
        key = f"await_details:{m.from_user.id}"
        r = await redis_pool.get(key)
        role = "Руководитель" if m.from_user.id == MANAGER_TELEGRAM_ID else "Сотрудник"

        if r:
            await redis_pool.delete(key)
            group, action = r.split("|", 1)
            if group == "Задачи" and action == "Добавить задачу":
                try:
                    tasks_svc.add_task(
                        title="Задача",
                        details=m.text,
                        assigned_to=m.from_user.id,
                        created_by=m.from_user.id
                    )
                except Exception:
                    logger.exception("Failed to add task")
                await m.answer("Задача добавлена ✅")
                return
            if group == "Отчетность" and action == "Создать отчет":
                rep_tid = baserow.get_table_id_by_name("Собрание, рабочие процессы")
                rep_tid = await _maybe_await(rep_tid)
                if rep_tid:
                    try:
                        baserow.create_row(rep_tid, {
                            "title": "Отчет",
                            "notes": m.text,
                            "date": datetime.datetime.utcnow().isoformat(),
                            "owner_tg": m.from_user.id
                        })
                    except Exception:
                        logger.exception("Failed to create report row")
                if MANAGER_TELEGRAM_ID:
                    await bot.send_message(
                        MANAGER_TELEGRAM_ID,
                        f"Ежедневный отчет от {m.from_user.full_name}:\n{m.text}"
                    )
                await m.answer("Отчет сформирован и отправлен руководителю ✅")
                return

        # AI reply (awaited)
        reply = await ai_reply(role, m.text, policy_text)
        await m.answer(reply)

        await remember(m.from_user.id, role, m.text, {"source": "text"})

    @dp.callback_query(F.data == "action:Отчетность:Закончить рабочий день")
    async def finish_workday_request(c: CallbackQuery):
        uid = c.from_user.id
        today = datetime.date.today().isoformat()
        tid = await _maybe_await(baserow.get_table_id_by_name("Успешные Сделки"))
        total_comm, cnt = 0, 0
        if tid:
            rows_res = await _maybe_await(baserow.list_rows(tid, size=1000))
            rows = (rows_res or {}).get("results", []) if isinstance(rows_res, dict) else (rows_res or [])
            for r in rows:
                try:
                    if int(r.get("agent_id") or 0) == uid and (r.get("date") or "").startswith(today):
                        total_comm += int(r.get("commission_amount") or 0)
                        cnt += 1
                except Exception:
                    continue
        cash_tid = await _maybe_await(baserow.get_table_id_by_name("Общак"))
        my_fines = 0
        if cash_tid:
            rows_res = await _maybe_await(baserow.list_rows(cash_tid, size=1000))
            rows = (rows_res or {}).get("results", []) if isinstance(rows_res, dict) else (rows_res or [])
            for r in rows:
                try:
                    if int(r.get("from_agent") or 0) == uid and (r.get("date") or "").startswith(today) and r.get("type") == "Штраф":
                        my_fines += int(r.get("amount") or 0)
                except Exception:
                    continue
        net = total_comm - my_fines
        report_text = f"Отчет за {today} для {c.from_user.full_name}:\nСделки: {cnt} (комиссия {total_comm}), штрафы: {my_fines}, чистыми: {net}"
        await redis_pool.set(f"pending_finish:{uid}", report_text, ex=3600)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Подтвердить и отправить", callback_data="confirm_finish:yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="confirm_finish:no")
        ]])
        await c.message.answer(report_text)
        await c.message.answer("Подтвердите завершение рабочего дня:", reply_markup=kb)

    @dp.callback_query(F.data.startswith("confirm_finish:"))
    async def confirm_finish_handler(c: CallbackQuery):
        action = c.data.split(":", 1)[1]
        uid = c.from_user.id
        pending = await redis_pool.get(f"pending_finish:{uid}")
        if action == "no" or not pending:
            await c.message.answer("Операция отменена.")
            await redis_pool.delete(f"pending_finish:{uid}")
            return
        report_text = pending
        if MANAGER_TELEGRAM_ID:
            await bot.send_message(MANAGER_TELEGRAM_ID, report_text)
        rep_tid = await _maybe_await(baserow.get_table_id_by_name("Собрание, рабочие процессы"))
        if rep_tid:
            try:
                baserow.create_row(rep_tid, {
                    "title": f"Отчет {c.from_user.full_name}",
                    "notes": report_text,
                    "date": datetime.datetime.utcnow().isoformat(),
                    "owner_tg": uid
                })
            except Exception:
                logger.exception("Failed to create confirm_finish row")
        await c.message.answer("Рабочий день завершён. Отчет отправлен руководителю.")
        await redis_pool.delete(f"pending_finish:{uid}")

    # Polling loop
    try:
        # Optionally run on_startup tasks:
        await on_startup(bot)
        await dp.start_polling(bot, skip_updates=True)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await bot.session.close()
        await redis_pool.close()

if __name__ == "__main__":
    asyncio.run(main())
