import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from aiocryptopay import AioCryptoPay, Networks
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Update
from fastapi import FastAPI, Request

from bot.config import CRYPTO_TOKEN, TOKEN, WH_URL
from bot.database import initialize_database, DB_NAME
from bot.database.admin.admin import add_admin
from bot.handlers.admin.mailing import ensure_reward_buttons_schema
from bot.handlers.routers.routers import user_routers, admin_routers, start_router

from aiohttp import web

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

crypto_bot_token = CRYPTO_TOKEN
tg_bot_token = TOKEN  # === MAIN
router = Router()

bot = Bot(token=tg_bot_token)
dp = Dispatcher()

crypto = AioCryptoPay(
    token=CRYPTO_TOKEN,
    network=Networks.TEST_NET  # либо TEST_NET, если вы тестируете
)

web_app = web.Application()
web_app.add_routes([web.post('/crypto-secret-path', crypto.get_updates)])

# WEBHOOK_PATH = f'/bot/{tg_bot_token}'
# WEBHOOK_PATH_URL = f'{WH_URL}{WEBHOOK_PATH}'
#
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     initialize_database()
#     ensure_reward_buttons_schema()
#     add_admin(DB_NAME, 6588562022)
#     add_admin(DB_NAME, 2099777407)
#     add_admin(DB_NAME, 1001605513)
#
#     await user_routers(dp)
#     await admin_routers(dp)
#     await start_router(dp)
#     dp.include_router(router)
#
#     wh_info = await bot.get_webhook_info()
#     if wh_info.url != WEBHOOK_PATH_URL:
#         await bot.set_webhook(url=WEBHOOK_PATH_URL)
#
#     logging.info("Сервер запущен и инициализирован.")
#     yield
#     await bot.session.close()
#
#
# app = FastAPI(lifespan=lifespan)
#
#
# @app.post(WEBHOOK_PATH)
# async def telegram_webhook(request: Request):
#     update_data = await request.json()
#     telegram_update = Update(**update_data)
#     await dp.process_update(telegram_update)
#     return {"ok": True}
#
#
# if __name__ == "__main__":
#     uvicorn.run(app, host='0.0.0.0', port=8080)

async def main():
    dp = Dispatcher()

    initialize_database()
    ensure_reward_buttons_schema()
    add_admin(DB_NAME, 6588562022)
    add_admin(DB_NAME, 2099777407)
    add_admin(DB_NAME, 1001605513)
    await user_routers(dp)
    await admin_routers(dp)
    await start_router(dp)
    dp.include_router(router)

    await asyncio.gather(
        dp.start_polling(bot)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user")
