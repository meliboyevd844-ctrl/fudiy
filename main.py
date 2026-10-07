import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, WEBAPP_HOST, WEBAPP_PORT
from database.db import init_db
from handlers import setup_routers
from webapp.server import create_webapp_app
from services.scheduler_service import setup_scheduler

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def start_webapp_server(app: web.Application, host: str, port: int):
    """Start the aiohttp WebApp server asynchronously."""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("WebApp scanner server running on http://%s:%d", host, port)
    return runner


async def main():
    logger.info("Starting Keldi-Ketdi Telegram Bot System...")

    # 1. Initialize Database
    await init_db()

    # 2. Check Bot Token
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.warning("DIQQAT: .env faylida BOT_TOKEN ko'rsatilmagan! Iltimos, @BotFather dan olingan bot tokeningizni .env fayliga kiriting.")
        print("\n" + "=" * 60)
        print("DIQQAT: .env faylida BOT_TOKEN kiritilmagan!")
        print("Iltimos, @BotFather dan olgan bot tokeningizni .env fayliga yozing:")
        print("BOT_TOKEN=123456789:ABCdef...")
        print("=" * 60 + "\n")

    # 3. Setup Bot & Dispatcher
    bot = Bot(token=BOT_TOKEN if BOT_TOKEN else "123456:dummy_token_for_init")
    dp = Dispatcher(storage=MemoryStorage())
    setup_routers(dp)

    # 4. Setup Scheduler
    scheduler = setup_scheduler(bot)

    # 5. Setup WebApp Server
    webapp_app = create_webapp_app(bot)
    webapp_runner = await start_webapp_server(webapp_app, WEBAPP_HOST, WEBAPP_PORT)

    # 6. Start Polling with Automatic Network Reconnect
    if BOT_TOKEN and BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.info("Telegram Bot Polling started...")
        while True:
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
                break
            except Exception as e:
                logger.warning("Tarmoq xatoligi yuz berdi: %s. 3 soniyadan so'ng qayta ulanadi...", e)
                await asyncio.sleep(3)
        
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        await webapp_runner.cleanup()
        await bot.session.close()
    else:
        logger.info("Running in WebApp standalone mode (Bot token is empty). Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            scheduler.shutdown(wait=False)
            await webapp_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
