from aiogram import Router


async def user_routers(dp) -> Router():
    from ..user.games import router as user_games_router
    from ..user.replenish import router as user_replenish_router
    from ..user.get_reward import router as user_get_reward_router
    from ..user.transfer_balance import router as user_trade_balance_router
    from ..user.office import router as user_office_router
    from ..user.referral_system import router as user_referral_system_router
    from ..user.checkout_balance import router as user_checkout_balance_router
    from ..user.inline_send import router as user_inline_send_router
    from ..user.activate_promo import router as user_activate_promo_router

    dp.include_router(user_games_router)
    dp.include_router(user_activate_promo_router)
    dp.include_router(user_replenish_router)
    dp.include_router(user_get_reward_router)
    dp.include_router(user_trade_balance_router)
    dp.include_router(user_office_router)
    dp.include_router(user_referral_system_router)
    dp.include_router(user_checkout_balance_router)
    dp.include_router(user_inline_send_router)


async def admin_routers(dp) -> Router():
    from ..admin.admin_panel import router as admin_router
    from ..admin.view_users import router as admin_view_users
    from ..admin.mailing import router as admin_mailing_router
    from ..admin.adjust_referral_percent import router as admin_adjust_referral_percent
    from ..admin.percentage import router as admin_percentage_router
    from ..admin.set_images import router as admin_set_images_router
    from ..admin.create_promo import router as admin_promos_router
    from ..admin.promo_settings import router as admin_promos_settings
    from ..admin.mailing_settings import router as admin_mailing_settings

    dp.include_router(admin_mailing_settings)
    dp.include_router(admin_router)
    dp.include_router(admin_promos_router)
    dp.include_router(admin_mailing_router)
    dp.include_router(admin_promos_settings)
    dp.include_router(admin_set_images_router)
    dp.include_router(admin_view_users)
    dp.include_router(admin_adjust_referral_percent)
    dp.include_router(admin_percentage_router)


async def start_router(dp) -> Router():
    from ..command_start import router as command_start_router

    dp.include_router(command_start_router)
