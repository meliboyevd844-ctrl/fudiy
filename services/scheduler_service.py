import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database.queries import (
    get_setting,
    get_employees_without_arrival,
    mark_absent_if_not_present,
    get_all_admin_ids,
)

logger = logging.getLogger(__name__)

async def run_daily_absence_check(bot: Bot):
    """
    Automated job to check employees who did not check in by shift start + grace period.
    Marks them as absent and asks them for their explanation reason.
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    work_start = await get_setting("work_start_time", "09:00")
    logger.info("Running daily absence check for date %s", today_str)

    absent_employees = await get_employees_without_arrival(today_str)
    if not absent_employees:
        logger.info("All employees have arrived today or no approved employees.")
        return

    admin_ids = await get_all_admin_ids()
    absent_names = []

    for emp in absent_employees:
        emp_id = emp["id"]
        tg_id = emp["telegram_id"]
        full_name = emp["full_name"]
        absent_names.append(full_name)

        # Mark as absent in DB
        await mark_absent_if_not_present(emp_id, today_str)

        # Send inquiry message to employee if telegram_id exists
        if tg_id:
            try:
                msg = (
                    f"⚠️ <b>Hurmatli {full_name}!</b>\n\n"
                    f"Siz bugun (<b>{today_str}</b>) belgilangan ish vaqti (<b>{work_start}</b>) bo'yicha ishga kelmadingiz.\n\n"
                    f"❓ <b>Kelmaganligingizning sababi bormi?</b>\n"
                    f"Iltimos, sababini to'g'ridan-to'g'ri ushbu botga matn shaklida yozib yuboring (masalan: <i>'Kasal bo'lib qoldim'</i> yoki <i>'Zarur oilaviy sabab'</i>).\n\n"
                    f"Siz yozgan sabab to'g'ridan-to'g'ri rahbariyatga yetkaziladi."
                )
                await bot.send_message(chat_id=tg_id, text=msg, parse_mode="HTML")
            except Exception as e:
                logger.error("Failed to send absence notice to %s (%s): %s", full_name, tg_id, e)

    # Notify Admins
    if admin_ids:
        emp_list_str = "\n".join([f"• 👤 {name}" for name in absent_names])
        admin_alert = (
            f"🚨 <b>KUNLIK KELMADILAR HISOBOTI ({today_str})</b>\n\n"
            f"Quyidagi xodimlar bugun belgilangan vaqtda kelmadi ({len(absent_names)} nafar):\n\n"
            f"{emp_list_str}\n\n"
            f"💬 Barcha kelmagan xodimlarga avtomatik tarzda sababini so'rab xabar yuborildi. Ular javob bersa sizga bildirishnoma keladi."
        )
        for admin_id in admin_ids:
            try:
                await bot.send_message(chat_id=admin_id, text=admin_alert, parse_mode="HTML")
            except Exception as e:
                logger.error("Failed to notify admin %s: %s", admin_id, e)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Setup and configure the APScheduler for periodic tasks."""
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    # Schedule daily check at 09:30 AM Tashkent time (or every day)
    scheduler.add_job(
        run_daily_absence_check,
        trigger="cron",
        hour=9,
        minute=30,
        args=[bot],
        id="daily_absence_check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with Asia/Tashkent timezone")
    return scheduler
