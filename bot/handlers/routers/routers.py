from ..user.games import router as user_games_router

from aiogram import Router


async def user_routers(dp) -> Router():
    dp.include_router(user_games_router)
