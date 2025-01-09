from aiogram import Router


async def user_routers(dp) -> Router():
    from ..user.games import router as user_games_router
    from ..user.replenish import router as user_replenish_router

    dp.include_router(user_games_router)
    dp.include_router(user_replenish_router)


async def admin_routers(dp) -> Router():
    from ..admin.admin_panel import router as admin_router
    from ..admin.view_users import router as admin_view_users

    dp.include_router(admin_router)
    dp.include_router(admin_view_users)
