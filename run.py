import aiosqlite
import asyncio

from aiogram import Dispatcher,Bot

from config import TOKEN

from handlers import router

from models import async_main

import sys
import os


bot=Bot(token=TOKEN)
dp=Dispatcher()



async def main():
    print("Телеграм бот запущен успешно!\nЧтобы проверить его работу, напишите боту /start в Telegram: @dzheman_gpt_bot")
    await async_main()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("Exit")
