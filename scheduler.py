# bot/scheduler.py
import asyncio
import inspect
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.services.finance import FinanceService
from bot.services.baserow_client import Baserow
from bot.config import MANAGER_TELEGRAM_ID

logger = logging.getLogger(__name__)

async def _maybe_await(val):
    if inspect.isawaitable(val):
        return await val
    return val

def start_scheduler(loop, bot):
    scheduler = AsyncIOScheduler(event_loop=loop)
    baserow = Baserow()
    finance = FinanceService(baserow)

    async def daily_report_job():
        try:
            t = await _maybe_await(baserow.get_table_id_by_name("Успешные Сделки"))
            if not t:
                return
            rows_res = await _maybe_await(baserow.list_rows(t, size=1000))
            rows = (rows_res or {}).get("results", []) if isinstance(rows_res, dict) else (rows_res or [])
            agents = set()
            for r in rows:
                try:
                    aid = int(r.get("agent_id") or 0)
                    if aid:
                        agents.add(aid)
                except Exception:
                    continue
            if not agents:
                return
            text = "Ежедневный автоматический отчет по агентам:\n"
            for a in agents:
                try:
                    s = await _maybe_await(finance.summary_for_agent(a))
                    if isinstance(s, dict):
                        income = s.get("income")
                        penalties = s.get("penalties")
                        net = s.get("net")
                    else:
                        income = getattr(s, "income", None)
                        penalties = getattr(s, "penalties", None)
                        net = getattr(s, "net", None)
                    text += f"Agent {a}: доходы {income}, штрафы {penalties}, чистыми {net}\n"
                except Exception:
                    logger.exception("Error collecting summary for agent %s", a)
                    text += f"Agent {a}: ошибка при сборе данных\n"
            if MANAGER_TELEGRAM_ID:
                await bot.send_message(MANAGER_TELEGRAM_ID, text)
        except Exception:
            logger.exception("daily_report_job failure")

    scheduler.add_job(daily_report_job, "cron", hour=23, minute=59)
    scheduler.start()
    return scheduler
