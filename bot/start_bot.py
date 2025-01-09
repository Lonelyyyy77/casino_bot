import asyncio
import logging

from aiogram import Bot, Dispatcher, Router

from handlers.command_start import router as start_router

import dotenv
from dotenv import load_dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

# TOKEN = load_dotenv('TOKEN') - MY DOTENV TOKEN
# TOKEN='7772152147:AAHmceBDqzK8iaAw0eaq_gOAOFjlfklhhyY' - MY TOKEN
TOKEN = '7528650704:AAERfIwdgypUreghZdPzfiDY0ZGuWg2KsXE' #VANIN TOKEN
router = Router()


async def main():
    bot = Bot(token=str(TOKEN))
    dp = Dispatcher()

    dp.include_router(start_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
