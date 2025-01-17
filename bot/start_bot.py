import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router

#from bot.database import initialize_database, DB_NAME
from database import DB_NAME, initialize_database
from database.admin.admin import add_admin
from handlers.routers.routers import user_routers, admin_routers
from handlers.command_start import router as start_router

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
router = Router()

bot = Bot(token=TOKEN)

async def main():
    dp = Dispatcher()

    initialize_database(DB_NAME)
    add_admin(DB_NAME, 6588562022)

    await user_routers(dp)
    await admin_routers(dp)

    dp.include_router(start_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
