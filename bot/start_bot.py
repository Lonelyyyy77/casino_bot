import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router

from bot.handlers.routers.routers import user_routers
from handlers.command_start import router as start_router

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
router = Router()


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    await user_routers(dp)

    dp.include_router(start_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
