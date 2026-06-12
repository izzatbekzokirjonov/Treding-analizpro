import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import config
from database.db import init_db
from handlers import start, analysis, subscription, admin
from handlers import history, referral, market, calculator, signal, ai_chat
from middlewares.language import LanguageMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

_DOMAIN   = os.getenv("REPLIT_DOMAINS", "").split(",")[0].strip()
_PORT     = int(os.getenv("PORT", 3000))
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WEBHOOK_PATH = f"/wh/{config.BOT_TOKEN}"
WEBHOOK_URL  = f"https://{_DOMAIN}{WEBHOOK_PATH}"


async def main():
    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    # Routers — FSM handlers before catch-all analysis
    dp.include_router(start.router)
    dp.include_router(subscription.router)
    dp.include_router(admin.router)
    dp.include_router(signal.router)
    dp.include_router(ai_chat.router)
    dp.include_router(calculator.router)
    dp.include_router(history.router)
    dp.include_router(referral.router)
    dp.include_router(market.router)
    dp.include_router(analysis.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set: {WEBHOOK_URL}")

    await start.set_bot_commands(bot)

    app = web.Application()

    async def health(_):
        return web.Response(text="Bot is alive!")

    async def webapp_route(_):
        path = os.path.join(_BASE_DIR, "webapp.html")
        with open(path, encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/webapp", webapp_route)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", _PORT)
    await site.start()

    logger.info(f"Bot running on port {_PORT} (webhook mode)")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
