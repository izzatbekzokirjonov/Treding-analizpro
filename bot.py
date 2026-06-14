from keep_alive import keep_alive
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import init_db
from handlers import start, analysis, subscription, admin
from middlewares.language import LanguageMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    keep_alive()
    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    dp.include_router(start.router)
    dp.include_router(analysis.router)
    dp.include_router(subscription.router)
    dp.include_router(admin.router)

    logger.info("Bot starting with polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
