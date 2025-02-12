import asyncio
import logging
import os

from aiocryptopay import AioCryptoPay, Networks
from aiogram import Bot, Dispatcher, Router

from bot.config import CRYPTO_TOKEN, TOKEN
from bot.database import initialize_database, DB_NAME
from bot.database.admin.admin import add_admin
from bot.handlers.admin.mailing import ensure_reward_buttons_schema
from bot.handlers.routers.routers import user_routers, admin_routers, start_router

import asyncio
from aiohttp import web

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

crypto_bot_token = CRYPTO_TOKEN
tg_bot_token = TOKEN # === MAIN
# tg_bot_token = "6680111108:AAFPO3QE4vokIaCADVJTAOEKsvUQVKNSod8" # TEST
router = Router()

bot = Bot(token=tg_bot_token)

crypto = AioCryptoPay(
    token=CRYPTO_TOKEN,
    network=Networks.TEST_NET  # либо TEST_NET, если вы тестируете
)

web_app = web.Application()
web_app.add_routes([web.post('/crypto-secret-path', crypto.get_updates)])


async def start_web_app():
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    logging.info("Сервер запущен на http://localhost:8080")
    while True:
        await asyncio.sleep(3600)


async def main():
    dp = Dispatcher()

    initialize_database()
    ensure_reward_buttons_schema()
    add_admin(DB_NAME, 6588562022)
    add_admin(DB_NAME, 2099777407)
    await user_routers(dp)
    await admin_routers(dp)
    await start_router(dp)
    dp.include_router(router)

    await asyncio.gather(
        dp.start_polling(bot),
        start_web_app()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user")
