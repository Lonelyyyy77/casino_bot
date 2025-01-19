import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router

from database import initialize_database, DB_NAME
from database.admin.admin import add_admin
from handlers.routers.routers import user_routers, admin_routers, start_router

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
router = Router()

bot = Bot(token=TOKEN)


async def main():
    dp = Dispatcher()

    initialize_database()
    add_admin(DB_NAME, 6588562022)

    await user_routers(dp)
    await admin_routers(dp)
    await start_router(dp)

    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user")
