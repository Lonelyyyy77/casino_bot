from aiogram import Router


async def user_routers(dp) -> Router():
    from ..user.games import router as user_games_router

    dp.include_router(user_games_router)
