"""Start the Telegram shop with long polling."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation

from app.config import Settings
from app.database.models import async_main, engine
from app.handlers import router


async def main() -> None:
    settings = Settings.from_env()
    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher(events_isolation=SimpleEventIsolation())
    dispatcher.include_router(router)
    try:
        await async_main()
        logging.info("Starting shop polling")
        await dispatcher.start_polling(bot, admin_chat_id=settings.admin_chat_id)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
